"""月相（新月・満月）の計算

旧暦の計算で使っている朔（新月）の式をそのまま使い、満月は朔と朔の中間（k+0.5）として求める。
恋愛の記事では「新月＝始まり」「満月＝実り・手放し」として扱う。
"""

import math
from datetime import date, timedelta

from src.kyureki import DELTA_T_DAYS, _new_moon_jd

PHASE_NAMES = ["新月", "三日月", "上弦の月", "十三夜", "満月", "寝待月", "下弦の月", "有明の月"]
MOON_MEANING = {
    "新月": "願いごとや、新しい関係を始めるのに向く日",
    "満月": "気持ちが満ちる日。実りを受け取るか、手放すかを決める日",
}


def _phase_date(k: float) -> date:
    jd_ut = _new_moon_jd(k) - DELTA_T_DAYS
    return date.fromordinal(math.floor(jd_ut + 0.5 + 9 / 24) - 1721425)


def _k_near(d: date) -> float:
    return math.floor((d.year + (d.timetuple().tm_yday / 365.25) - 2000) * 12.3685)


def new_moons_between(start: date, end: date) -> list:
    base = _k_near(start)
    return [d for d in (_phase_date(base + i) for i in range(-2, 4)) if start <= d <= end]


def full_moons_between(start: date, end: date) -> list:
    base = _k_near(start)
    return [d for d in (_phase_date(base + i + 0.5) for i in range(-2, 4)) if start <= d <= end]


def last_new_moon(d: date) -> date:
    base = _k_near(d)
    candidates = [_phase_date(base + i) for i in range(2, -4, -1)]
    return max(x for x in candidates if x <= d)


def moon_age(d: date) -> int:
    return (d - last_new_moon(d)).days


def phase_name(d: date) -> str:
    """月の呼び名。新月・満月は概算ではなく、実際の朔・望の日と一致させる"""
    if d == last_new_moon(d):
        return "新月"
    if d in full_moons_between(d - timedelta(days=3), d + timedelta(days=3)):
        return "満月"
    age = moon_age(d)
    if age <= 5:
        return "三日月"
    if age <= 8:
        return "上弦の月"
    if age <= 13:
        return "十三夜"
    if age <= 16:
        upcoming = full_moons_between(d, d + timedelta(days=3))
        return "小望月" if upcoming else "十六夜"
    if age <= 21:
        return "寝待月"
    if age <= 24:
        return "下弦の月"
    return "有明の月"


def moon_events(start: date, end: date) -> list:
    """期間内の新月・満月を日付順に返す"""
    events = [{"date": d, "kind": "新月", "meaning": MOON_MEANING["新月"]} for d in new_moons_between(start, end)]
    events += [{"date": d, "kind": "満月", "meaning": MOON_MEANING["満月"]} for d in full_moons_between(start, end)]
    return sorted(events, key=lambda e: e["date"])


def next_event(d: date) -> dict:
    """d 以降で最初に来る新月か満月"""
    events = moon_events(d, d + timedelta(days=35))
    return events[0] if events else {}
