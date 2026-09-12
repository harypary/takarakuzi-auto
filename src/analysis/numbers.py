"""ナンバーズ3・4 の統計分析"""

from collections import Counter
from math import factorial

from src.analysis.stats import chi2_pvalue, percentile
from src.config import Game

POSITION_LABELS = {
    3: ("百の位", "十の位", "一の位"),
    4: ("千の位", "百の位", "十の位", "一の位"),
}
_PATTERNS = {
    (1, 1, 1, 1): "シングル", (2, 1, 1): "ダブル", (2, 2): "ダブルダブル", (3, 1): "トリプル", (4,): "クワッド",
    (1, 1, 1): "シングル", (2, 1): "ダブル", (3,): "トリプル",
}


def pattern_of(number: str) -> str:
    return _PATTERNS[tuple(sorted(Counter(number).values(), reverse=True))]


def box_ways(number: str) -> int:
    ways = factorial(len(number))
    for c in Counter(number).values():
        ways //= factorial(c)
    return ways


def analyze_numbers(game: Game, results: list) -> dict:
    d = game.digits
    seqs = [r["number"] for r in results]
    total = len(seqs)
    w30 = min(30, total)

    positions = []
    for p, label in enumerate(POSITION_LABELS[d]):
        col = [int(s[p]) for s in seqs]
        f30, f100, fall = Counter(col[-w30:]), Counter(col[-100:]), Counter(col)
        interval = {g: next((i for i, v in enumerate(reversed(col)) if v == g), total) for g in range(10)}
        expected = total / 10
        chi2 = sum((fall[g] - expected) ** 2 / expected for g in range(10))
        positions.append({
            "label": label,
            "f30": {g: f30[g] for g in range(10)},
            "f100": {g: f100[g] for g in range(10)},
            "interval": interval,
            "hot": sorted(range(10), key=lambda g: (-f30[g], -f100[g], g))[:3],
            "cold": sorted(range(10), key=lambda g: (-interval[g], g))[:3],
            "chi_p": chi2_pvalue(chi2, 9),
        })

    pattern_all = Counter(pattern_of(s) for s in seqs)
    pattern_30 = Counter(pattern_of(s) for s in seqs[-w30:])
    sums = [sum(int(c) for c in s) for s in seqs]
    sums_sorted = sorted(sums)
    repeat = [any(a == b for a, b in zip(seqs[i], seqs[i - 1])) for i in range(1, total)]
    digits_30 = Counter(c for s in seqs[-w30:] for c in s)

    return {
        "total": total,
        "last": results[-1],
        "positions": positions,
        "pattern_all": [(k, v / total) for k, v in pattern_all.most_common()],
        "pattern_30": [(k, v / w30) for k, v in pattern_30.most_common()],
        "sum_mean": sum(sums) / total,
        "sum_lo": percentile(sums_sorted, 0.10),
        "sum_hi": percentile(sums_sorted, 0.90),
        "recent_sums": sums[-10:],
        "recent": [(r["draw"], r["number"]) for r in results[-10:]],
        "repeat_rate": sum(repeat) / len(repeat),
        "digits_30": [(int(k), v) for k, v in digits_30.most_common(4)],
        "missing_30": [g for g in range(10) if digits_30.get(str(g), 0) == 0],
    }
