"""特徴量の計算と予想の生成

予想の数字はすべてここで決定的に計算する（LLMには数字を作らせない）。
同じデータ・同じ重み・同じ回号なら、何度実行しても同じ予想になる。
"""

import heapq
import itertools
import random
import zlib
from collections import Counter

from src.analysis.numbers import box_ways, pattern_of
from src.analysis.stats import percentile
from src.config import FEATURES, PICK_TIERS, Game
from src.koyomi import koyomi_digit_score, koyomi_number_score


# ロト系で1つの数字が10口中に登場する上限（偏りすぎ防止）
MAX_NUMBER_USAGE = 5


def seed_for(game: Game, draw: int) -> int:
    return zlib.crc32(f"{game.key}-{draw}".encode())


def _minmax(values: dict) -> dict:
    lo, hi = min(values.values()), max(values.values())
    if hi - lo < 1e-9:
        return {k: 0.0 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def score(feat: dict, weights: dict) -> float:
    return sum(weights[f] * feat[f] for f in FEATURES)


def tier_weights(weights: dict, tier: str) -> dict:
    w = dict(weights)
    if tier == "対抗":
        w["koyomi"] *= 2.0
    elif tier == "穴":
        w["cold"] *= 2.0
        w["hot"] *= 0.5
    total = sum(w.values())
    return {f: v / total for f, v in w.items()}


# ───────────────────────── 特徴量 ─────────────────────────

def loto_features(game: Game, results: list, ko: dict) -> dict:
    N, k = game.max_number, game.pick
    draws = [set(r["main"]) for r in results]
    total = len(draws)
    w20, w100 = min(20, total), min(100, total)
    f20 = Counter(n for d in draws[-w20:] for n in d)
    f100 = Counter(n for d in draws[-w100:] for n in d)
    last = draws[-1]
    mean_gap = N / k
    numbers = range(1, N + 1)
    hot = _minmax({n: f20[n] + f100[n] / 10 for n in numbers})
    trend = _minmax({n: f20[n] / w20 - f100[n] / w100 for n in numbers})

    feats = {}
    for n in numbers:
        interval = next((i for i, d in enumerate(reversed(draws)) if n in d), total)
        feats[n] = {
            "hot": hot[n],
            "trend": trend[n],
            "cold": min(interval / (mean_gap * 2), 1.0),
            "carry": 1.0 if n in last else 0.0,
            "slide": 1.0 if n not in last and (n - 1 in last or n + 1 in last) else 0.0,
            "koyomi": koyomi_number_score(n, ko),
        }
    return feats


def numbers_features(game: Game, results: list, ko: dict) -> list:
    d = game.digits
    seqs = [r["number"] for r in results]
    total = len(seqs)
    w30, w100 = min(30, total), min(100, total)
    last = seqs[-1]
    out = []
    for p in range(d):
        col = [int(s[p]) for s in seqs]
        f30, f100 = Counter(col[-w30:]), Counter(col[-w100:])
        hot = _minmax({g: f30[g] + f100[g] / 10 for g in range(10)})
        trend = _minmax({g: f30[g] / w30 - f100[g] / w100 for g in range(10)})
        last_digit = int(last[p])
        feats = {}
        for g in range(10):
            interval = next((i for i, v in enumerate(reversed(col)) if v == g), total)
            feats[g] = {
                "hot": hot[g],
                "trend": trend[g],
                "cold": min(interval / 20, 1.0),
                "carry": 1.0 if g == last_digit else 0.0,
                "slide": 1.0 if (g - last_digit) % 10 in (1, 9) else 0.0,
                "koyomi": koyomi_digit_score(g, p, d, ko),
            }
        out.append(feats)
    return out


def features_for(game: Game, results: list, ko: dict):
    return loto_features(game, results, ko) if game.kind == "loto" else numbers_features(game, results, ko)


# ───────────────────────── ロト系 ─────────────────────────

def _longest_run(combo) -> int:
    best = run = 1
    for a, b in zip(combo, combo[1:]):
        run = run + 1 if b - a == 1 else 1
        best = max(best, run)
    return best


def loto_constraints(game: Game, results: list) -> dict:
    sums = sorted(sum(r["main"]) for r in results)
    odd = Counter(sum(n % 2 for n in r["main"]) for r in results)
    allowed, covered = set(), 0
    for count, freq in odd.most_common():
        allowed.add(count)
        covered += freq
        if covered / len(results) >= 0.85:
            break
    return {
        "sum_lo": percentile(sums, 0.10),
        "sum_hi": percentile(sums, 0.90),
        "odd_allowed": sorted(allowed),
        "max_shared": game.pick // 2,
    }


def predict_loto(game: Game, results: list, ko: dict, weights: dict, seed: int) -> dict:
    k = game.pick
    feats = loto_features(game, results, ko)
    cons = loto_constraints(game, results)
    last = set(results[-1]["main"])
    rng = random.Random(seed)
    numbers = list(feats)

    selected, picks = [], []
    for tier, count in PICK_TIERS:
        w = tier_weights(weights, tier)
        sc = {n: score(feats[n], w) for n in numbers}
        cands = set()
        for _ in range(5000):
            chosen = heapq.nlargest(k, numbers, key=lambda n: rng.random() ** (1.0 / (sc[n] + 0.1) ** 2))
            combo = tuple(sorted(chosen))
            if combo in cands:
                continue
            if not cons["sum_lo"] <= sum(combo) <= cons["sum_hi"]:
                continue
            if sum(n % 2 for n in combo) not in cons["odd_allowed"]:
                continue
            if _longest_run(combo) > 2 or len(last & set(combo)) > 2:
                continue
            cands.add(combo)

        ranked = sorted(cands, key=lambda c: (-sum(sc[n] for n in c), c))
        got = 0
        for relax in range(3):
            for combo in ranked:
                if got == count:
                    break
                if combo in selected:
                    continue
                if any(len(set(combo) & set(s)) > cons["max_shared"] + relax for s in selected):
                    continue
                usage = Counter(n for s in selected for n in s)
                if any(usage[n] >= MAX_NUMBER_USAGE + relax for n in combo):
                    continue
                selected.append(combo)
                picks.append({
                    "tier": tier,
                    "numbers": list(combo),
                    "score": round(sum(sc[n] for n in combo) / k, 4),
                    "sum": sum(combo),
                    "odd": sum(n % 2 for n in combo),
                })
                got += 1
            if got == count:
                break

    base = {n: score(feats[n], weights) for n in numbers}
    ranked_numbers = sorted(numbers, key=lambda n: (-base[n], n))
    koyomi_numbers = sorted(sorted(numbers, key=lambda n: (-feats[n]["koyomi"], n))[: k + 2])
    return {
        "picks": picks,
        "axis": sorted(ranked_numbers[:3]),
        "exclude": sorted(ranked_numbers[-5:]),
        "koyomi_numbers": koyomi_numbers,
        "top": [
            {"n": n, "total": base[n], "parts": {f: weights[f] * feats[n][f] for f in FEATURES}}
            for n in ranked_numbers[:10]
        ],
        "constraints": cons,
        "weights": weights,
    }


# ───────────────────────── ナンバーズ ─────────────────────────

def _buy_hint(game: Game, number: str, tier: str, index: int) -> str:
    ways = box_ways(number)
    if ways == 1:
        return "ストレートのみ"
    if tier == "本命" and index == 0:
        return "ストレート＋ミニ" if game.digits == 3 else "ストレート"
    return f"セット（ボックス{ways}通り）"


def predict_numbers(game: Game, results: list, ko: dict, weights: dict, seed: int) -> dict:
    d = game.digits
    feats = numbers_features(game, results, ko)
    pattern_count = Counter(pattern_of(r["number"]) for r in results[-1000:])
    top_count = max(pattern_count.values())
    prior = {p: c / top_count for p, c in pattern_count.items()}
    combos = ["".join(t) for t in itertools.product("0123456789", repeat=d)]
    max_shared = d - 2

    selected, picks = [], []
    for tier, count in PICK_TIERS:
        w = tier_weights(weights, tier)
        pos_scores = [{g: score(feats[p][g], w) for g in range(10)} for p in range(d)]

        def combo_score(c):
            return sum(pos_scores[p][int(ch)] for p, ch in enumerate(c)) / d + 0.12 * prior.get(pattern_of(c), 0)

        scored = {c: combo_score(c) for c in combos}
        ranked = sorted(combos, key=lambda c: (-scored[c], c))
        got = 0
        for relax in range(d):
            for c in ranked:
                if got == count:
                    break
                if c in selected:
                    continue
                if any(sum(a == b for a, b in zip(c, s)) > max_shared + relax for s in selected):
                    continue
                # 同じボックス（数字の並べ替え）は1つだけにする
                if any(sorted(c) == sorted(s) for s in selected):
                    continue
                selected.append(c)
                picks.append({
                    "tier": tier,
                    "number": c,
                    "score": round(scored[c], 4),
                    "pattern": pattern_of(c),
                    "sum": sum(int(ch) for ch in c),
                    "buy": _buy_hint(game, c, tier, got),
                })
                got += 1
            if got == count:
                break

    base = [{g: score(feats[p][g], weights) for g in range(10)} for p in range(d)]
    top = [
        [{"g": g, "total": base[p][g]} for g in sorted(range(10), key=lambda g: (-base[p][g], g))[:3]]
        for p in range(d)
    ]
    return {
        "picks": picks,
        "axis": [[row["g"] for row in top[p][:2]] for p in range(d)],
        "top": top,
        "max_shared": max_shared,
        "weights": weights,
    }


def predict(game: Game, results: list, ko: dict, weights: dict, draw: int) -> dict:
    seed = seed_for(game, draw)
    if game.kind == "loto":
        return predict_loto(game, results, ko, weights, seed)
    return predict_numbers(game, results, ko, weights, seed)
