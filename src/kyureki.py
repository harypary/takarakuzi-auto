"""旧暦（日本時間基準）の日付計算と六曜

六曜は旧暦の (月 + 日) mod 6 で決まるため、旧暦の日付がずれると六曜もずれる。
中国暦のライブラリ（lunardate）は UTC+8 基準のため、新月が日本時間の深夜に起きる月は
朔日が1日ずれることがある。そこで朔（新月）の瞬間を Meeus の式で求め、
日本時間での朔日を基準に旧暦の日を数える。月の番号は lunardate の値を使う。
"""

import math
from datetime import date, timedelta
from functools import lru_cache

from lunardate import LunarDate

ROKUYO = ["大安", "赤口", "先勝", "友引", "先負", "仏滅"]
DELTA_T_DAYS = 70 / 86400  # 2026年ごろの TT-UT（約70秒）


def _jdn(d: date) -> int:
    return d.toordinal() + 1721425


def _new_moon_jd(k: float) -> float:
    """k 番目の朔のユリウス日（TT）。Meeus『Astronomical Algorithms』第49章"""
    t = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * t**2
           - 0.000000150 * t**3 + 0.00000000073 * t**4)
    e = 1 - 0.002516 * t - 0.0000074 * t**2
    m = math.radians((2.5534 + 29.10535670 * k - 0.0000014 * t**2 - 0.00000011 * t**3) % 360)
    mp = math.radians((201.5643 + 385.81693528 * k + 0.0107582 * t**2
                       + 0.00001238 * t**3 - 0.000000058 * t**4) % 360)
    f = math.radians((160.7108 + 390.67050284 * k - 0.0016118 * t**2
                      - 0.00000227 * t**3 + 0.000000011 * t**4) % 360)
    omega = math.radians((124.7746 - 1.56375588 * k + 0.0020672 * t**2 + 0.00000215 * t**3) % 360)

    correction = (
        -0.40720 * math.sin(mp)
        + 0.17241 * e * math.sin(m)
        + 0.01608 * math.sin(2 * mp)
        + 0.01039 * math.sin(2 * f)
        + 0.00739 * e * math.sin(mp - m)
        - 0.00514 * e * math.sin(mp + m)
        + 0.00208 * e * e * math.sin(2 * m)
        - 0.00111 * math.sin(mp - 2 * f)
        - 0.00057 * math.sin(mp + 2 * f)
        + 0.00056 * e * math.sin(2 * mp + m)
        - 0.00042 * math.sin(3 * mp)
        + 0.00042 * e * math.sin(m + 2 * f)
        + 0.00038 * e * math.sin(m - 2 * f)
        - 0.00024 * e * math.sin(2 * mp - m)
        - 0.00017 * math.sin(omega)
        - 0.00007 * math.sin(mp + 2 * m)
        + 0.00004 * math.sin(2 * mp - 2 * f)
        + 0.00004 * math.sin(3 * m)
        + 0.00003 * math.sin(mp + m - 2 * f)
        + 0.00003 * math.sin(2 * mp + 2 * f)
        - 0.00003 * math.sin(mp + m + 2 * f)
        + 0.00003 * math.sin(mp - m + 2 * f)
        - 0.00002 * math.sin(mp - m - 2 * f)
        - 0.00002 * math.sin(3 * mp + m)
        + 0.00002 * math.sin(4 * mp)
    )
    return jde + correction


def _new_moon_date(k: float) -> date:
    """k 番目の朔の日（日本時間）"""
    jd_ut = _new_moon_jd(k) - DELTA_T_DAYS
    return date.fromordinal(math.floor(jd_ut + 0.5 + 9 / 24) - 1721425)


@lru_cache(maxsize=None)
def shuo_date_on_or_before(d: date) -> date:
    """d 以前で最も近い朔日（旧暦1日にあたる日、日本時間）"""
    k = math.floor((d.year + (d.timetuple().tm_yday / 365.25) - 2000) * 12.3685)
    for candidate in range(int(k) + 2, int(k) - 3, -1):
        nm = _new_moon_date(candidate)
        if nm <= d:
            return nm
    raise ValueError(f"朔日を特定できません: {d}")


def lunar_month_day(d: date) -> tuple:
    """(旧暦の月, 旧暦の日)。月は中国暦の値、日は日本時間の朔日から数える"""
    shuo = shuo_date_on_or_before(d)
    day = (d - shuo).days + 1
    to_lunar = getattr(LunarDate, "from_solar_date", None) or LunarDate.fromSolarDate
    month = to_lunar(shuo.year, shuo.month, shuo.day).month
    return month, day


def rokuyo(d: date) -> str:
    month, day = lunar_month_day(d)
    return ROKUYO[(month + day) % 6]
