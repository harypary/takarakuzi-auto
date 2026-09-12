"""1記事分のデータ準備（分析・学習・予想・回顧）"""

from datetime import timedelta

from src.analysis.loto import analyze_loto
from src.analysis.numbers import analyze_numbers
from src.config import Game
from src.koyomi import koyomi
from src.predict.checker import evaluate
from src.predict.engine import predict
from src.predict.learning import ensure_weekly
from src.predict.store import load_prediction
from src.utils.dates import draw_number_for, to_date, week_start


def _review_draw(game: Game, history: list, index: int, weights: dict) -> dict:
    r = history[index]
    saved = load_prediction(game.key, r["draw"])
    if saved and saved.get("post", {}).get("url"):
        picks, backtest = saved["picks"], False
    else:
        d = to_date(r["date"])
        picks = predict(game, history[:index], koyomi(d), weights, r["draw"])["picks"]
        backtest = True
    ev = evaluate(game, picks, r)
    return {"draw": r["draw"], "date": r["date"], "result": r, "evals": ev["evals"], "best": ev["best"],
            "backtest": backtest}


def prepare_game(game: Game, results: list, target, persist: bool) -> dict:
    target = to_date(target)
    history = [r for r in results if to_date(r["date"]) < target]
    last = history[-1]
    draw = draw_number_for(game, last["draw"], to_date(last["date"]), target)

    weekly = ensure_weekly(game, history, target, persist)
    weights = weekly["after"]
    ko = koyomi(target)
    analysis = analyze_loto(game, history) if game.kind == "loto" else analyze_numbers(game, history)
    pred = predict(game, history, ko, weights, draw)

    ws = week_start(target)
    prev_start = ws - timedelta(days=7)
    review_prev, review_cur = [], []
    for i, r in enumerate(history):
        d = to_date(r["date"])
        if prev_start <= d < ws:
            review_prev.append(_review_draw(game, history, i, weekly["before"]))
        elif ws <= d < target:
            review_cur.append(_review_draw(game, history, i, weights))

    return {
        "game": game,
        "draw": draw,
        "date": target,
        "last": last,
        "ko": ko,
        "analysis": analysis,
        "pred": pred,
        "weekly": weekly,
        "review_prev": review_prev,
        "review_cur": review_cur,
    }


def is_posted(ctx: dict) -> bool:
    saved = load_prediction(ctx["game"].key, ctx["draw"])
    return bool(saved and saved.get("post", {}).get("url"))


def prediction_record(ctx: dict, series_key: str, url: str, posted_at: str) -> dict:
    pred = ctx["pred"]
    return {
        "game": ctx["game"].key,
        "draw": ctx["draw"],
        "date": ctx["date"].isoformat(),
        "weights": pred["weights"],
        "koyomi": ctx["ko"],
        "picks": pred["picks"],
        "axis": pred["axis"],
        "post": {"series": series_key, "url": url, "posted_at": posted_at},
    }
