"""週次学習：先週の抽せんで各分析軸がどれだけ機能したかを測り、今週の重みに反映する

- 各軸の成績 = その軸だけで選んだ上位の数字に、当せん数字がいくつ入ったか
  （ロト: 上位 pick×2 個 / ナンバーズ: 各桁の上位3数字）
- 偶然の期待値との比（リフト）に応じて重みを指数的に増減し、合計1に正規化
- 1週間で動く幅は抽せん回数に応じて抑え、各重みは5%〜40%に収める
"""

import math
from datetime import timedelta

from src.config import DEFAULT_WEIGHTS, FEATURES, Game
from src.koyomi import koyomi
from src.predict.engine import features_for
from src.predict.store import load_state, save_state
from src.utils.dates import to_date, week_start

W_MIN, W_MAX = 0.05, 0.40
KEEP_WEEKS = 52


def feature_performance(game: Game, feats, result: dict) -> dict:
    perf = {}
    if game.kind == "loto":
        top_k = game.pick * 2
        actual = set(result["main"])
        baseline = top_k * game.pick / game.max_number
        for f in FEATURES:
            top = sorted(feats, key=lambda n: (-feats[n][f], -feats[n]["hot"], n))[:top_k]
            perf[f] = {"hits": len(actual & set(top)), "baseline": round(baseline, 3)}
    else:
        d = game.digits
        for f in FEATURES:
            hits = 0
            for p in range(d):
                top = sorted(range(10), key=lambda g: (-feats[p][g][f], -feats[p][g]["hot"], g))[:3]
                hits += int(result["number"][p]) in top
            perf[f] = {"hits": hits, "baseline": round(0.3 * d, 3)}
    return perf


def update_weights(weights: dict, perfs: list) -> dict:
    if not perfs:
        return dict(weights)
    eta = min(0.4, 0.08 * len(perfs))
    new = {}
    for f in FEATURES:
        hits = sum(p[f]["hits"] for p in perfs)
        base = sum(p[f]["baseline"] for p in perfs)
        lift = max(-1.0, min(1.0, (hits - base) / base)) if base else 0.0
        new[f] = weights[f] * math.exp(eta * lift)
    for _ in range(10):
        total = sum(new.values())
        new = {f: min(W_MAX, max(W_MIN, v / total)) for f, v in new.items()}
    total = sum(new.values())
    return {f: round(v / total, 4) for f, v in new.items()}


def _weights_before(state: dict, ws_iso: str) -> dict:
    earlier = sorted(k for k in state["weeks"] if k < ws_iso)
    return dict(state["weeks"][earlier[-1]]["after"]) if earlier else dict(DEFAULT_WEIGHTS)


def ensure_weekly(game: Game, history: list, target, persist: bool) -> dict:
    """target 抽せん日の週の重みを確定する（先週の結果で学習。週内は再計算しない）"""
    ws = week_start(to_date(target))
    ws_iso = ws.isoformat()
    state = load_state(game.key)
    if ws_iso in state["weeks"]:
        return state["weeks"][ws_iso]

    prev_start, prev_end = ws - timedelta(days=7), ws - timedelta(days=1)
    before = _weights_before(state, ws_iso)
    perfs, items = [], []
    for i, r in enumerate(history):
        d = to_date(r["date"])
        if not prev_start <= d <= prev_end or i < 100:
            continue
        feats = features_for(game, history[:i], koyomi(d))
        perf = feature_performance(game, feats, r)
        perfs.append(perf)
        items.append({"draw": r["draw"], "date": r["date"], "perf": perf})

    totals = {
        f: {
            "hits": sum(p[f]["hits"] for p in perfs),
            "baseline": round(sum(p[f]["baseline"] for p in perfs), 3),
        }
        for f in FEATURES
    }
    record = {
        "week_start": ws_iso,
        "review_start": prev_start.isoformat(),
        "review_end": prev_end.isoformat(),
        "draws": items,
        "totals": totals,
        "before": before,
        "after": update_weights(before, perfs),
    }
    if persist:
        state["weeks"][ws_iso] = record
        for old in sorted(state["weeks"])[:-KEEP_WEEKS]:
            del state["weeks"][old]
        save_state(game.key, state)
    return record
