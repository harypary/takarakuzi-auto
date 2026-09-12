"""ロト系（ロト6・ロト7・ミニロト）の統計分析"""

import math
from collections import Counter
from itertools import combinations

from src.analysis.stats import chi2_pvalue, percentile
from src.config import Game


def analyze_loto(game: Game, results: list) -> dict:
    N, k = game.max_number, game.pick
    draws = [r["main"] for r in results]
    sets = [set(d) for d in draws]
    total = len(draws)
    w20, w100 = min(20, total), min(100, total)
    p = k / N

    def freq(w):
        c = Counter(n for d in draws[-w:] for n in d)
        return {n: c.get(n, 0) for n in range(1, N + 1)}

    f20, f100, fall = freq(w20), freq(w100), freq(total)
    sd100 = math.sqrt(w100 * p * (1 - p))
    interval = {n: next((i for i, s in enumerate(reversed(sets)) if n in s), total) for n in range(1, N + 1)}

    carry = [len(sets[i] & sets[i - 1]) for i in range(1, total)]
    slide = [
        sum(1 for n in sets[i] if n not in sets[i - 1] and (n - 1 in sets[i - 1] or n + 1 in sets[i - 1]))
        for i in range(1, total)
    ]
    carry_c = Counter(carry)

    sums = [sum(d) for d in draws]
    sums_sorted = sorted(sums)
    sum_mean = sum(sums) / total
    sum_std = math.sqrt(sum((s - sum_mean) ** 2 for s in sums) / total)

    odd_all = Counter(sum(n % 2 for n in d) for d in draws)
    odd_20 = Counter(sum(n % 2 for n in d) for d in draws[-w20:])
    low_max = N // 2
    lows = [sum(1 for n in d if n <= low_max) for d in draws]
    consec = [any(b - a == 1 for a, b in zip(d, d[1:])) for d in draws]
    pairs = Counter(pr for d in draws[-w100:] for pr in combinations(sorted(d), 2))

    expected_all = total * k / N
    chi2 = sum((fall[n] - expected_all) ** 2 / expected_all for n in fall)

    return {
        "total": total,
        "last": results[-1],
        "f20": f20,
        "f100": f100,
        "fall": fall,
        "z100": {n: (f100[n] - w100 * p) / sd100 for n in f100},
        "e20": w20 * p,
        "e100": w100 * p,
        "mean_gap": N / k,
        "interval": interval,
        "hot": sorted(f20, key=lambda n: (-f20[n], -f100[n], n))[:10],
        "cold": sorted(interval, key=lambda n: (-interval[n], n))[:10],
        "carry_mean": sum(carry) / len(carry),
        "carry_dist": {
            0: carry_c.get(0, 0) / len(carry),
            1: carry_c.get(1, 0) / len(carry),
            2: sum(v for c, v in carry_c.items() if c >= 2) / len(carry),
        },
        "slide_mean": sum(slide) / len(slide),
        "sum_mean": sum_mean,
        "sum_std": sum_std,
        "sum_lo": percentile(sums_sorted, 0.10),
        "sum_hi": percentile(sums_sorted, 0.90),
        "recent_sums": sums[-10:],
        "odd_top_all": [(c, v / total) for c, v in odd_all.most_common(3)],
        "odd_top_20": [(c, v / w20) for c, v in odd_20.most_common(3)],
        "low_max": low_max,
        "low_mean": sum(lows) / total,
        "low_mean_20": sum(lows[-w20:]) / w20,
        "consec_all": sum(consec) / total,
        "consec_20": sum(consec[-w20:]) / w20,
        "top_pairs": pairs.most_common(5),
        "pair_expected": w100 * (k * (k - 1)) / (N * (N - 1)),
        "chi2": chi2,
        "chi_p": chi2_pvalue(chi2, N - 1),
        "carryover": results[-1].get("carryover", 0),
    }
