"""統計の小道具"""

import math


def chi2_pvalue(chi2: float, df: int) -> float:
    """カイ二乗分布の上側確率（Wilson-Hilferty 近似）"""
    if df <= 0:
        return 1.0
    z = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return 0.5 * math.erfc(z / math.sqrt(2))


def percentile(sorted_values: list, q: float):
    idx = int(round(q * (len(sorted_values) - 1)))
    return sorted_values[min(len(sorted_values) - 1, max(0, idx))]
