"""暦の計算（干支・九星・六曜・節月・暦注の吉日・五行・数秘）

- 干支: ユリウス日から算出（2000-01-01 = 戊午）
- 節月・冬至/夏至: 太陽黄経の略算式（誤差は数分〜数十分程度）
- 九星（日盤）: 冬至/夏至に最も近い甲子日を陽遁/陰遁の起点とする方式（閏の特殊処理は省略）
- 六曜: 旧暦（lunardate の中国暦で近似）の (月+日) mod 6
"""

import math
from datetime import date, timedelta
from functools import lru_cache

from src.kyureki import ROKUYO, rokuyo  # noqa: F401  （他モジュールからの参照用に再エクスポート）

JIKKAN = "甲乙丙丁戊己庚辛壬癸"
JUNISHI = "子丑寅卯辰巳午未申酉戌亥"
KYUSEI_NAMES = ["", "一白水星", "二黒土星", "三碧木星", "四緑木星", "五黄土星", "六白金星", "七赤金星", "八白土星", "九紫火星"]
KYUSEI_GOGYO = [None, "水", "土", "木", "木", "土", "金", "金", "土", "火"]
KAN_GOGYO = "木木火火土土金金水水"
# 河図の数（五行ごとの数字）
GOGYO_DIGITS = {"水": (1, 6), "火": (2, 7), "木": (3, 8), "金": (4, 9), "土": (5, 0)}
SOJO = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # A が B を生む
SETSU_NAMES = ["立春", "啓蟄", "清明", "立夏", "芒種", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
SETSU_BRANCHES = "寅卯辰巳午未申酉戌亥子丑"
# 一粒万倍日: 節月（寅月=0）ごとの日の十二支
ICHIRYU = ["丑午", "寅酉", "子卯", "卯辰", "巳午", "酉午", "子未", "卯申", "午酉", "酉戌", "亥子", "卯子"]
# 天赦日: 季節（節月で判定）ごとの干支
TENSHA = {0: "戊寅", 1: "戊寅", 2: "戊寅", 3: "甲午", 4: "甲午", 5: "甲午",
          6: "戊申", 7: "戊申", 8: "戊申", 9: "甲子", 10: "甲子", 11: "甲子"}


def _jdn(d: date) -> int:
    return d.toordinal() + 1721425


def kanshi_index(d: date) -> int:
    return (_jdn(d) + 49) % 60


def kanshi(d: date) -> str:
    i = kanshi_index(d)
    return JIKKAN[i % 10] + JUNISHI[i % 12]


def _sun_longitude(jd: float) -> float:
    n = jd - 2451545.0
    mean_l = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    return (mean_l + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360


def _jd_jst_midnight(d: date) -> float:
    """JST 0:00 のユリウス日（= 前日 UT 15:00）"""
    return _jdn(d) - 0.5 - 9 / 24


def setsu_month(d: date) -> int:
    """節月（寅月=0 … 丑月=11）。その日のうちに節入りすれば新しい月とみなす"""
    lam = _sun_longitude(_jd_jst_midnight(d + timedelta(days=1)))
    return int(((lam - 315) % 360) // 30)


@lru_cache(maxsize=None)
def crossing_date(year: int, month: int, target_longitude: float) -> date:
    """太陽黄経が target を通過する日（JST）。month の15〜28日を探索"""
    for day in range(15, 29):
        d = date(year, month, day)
        a = _sun_longitude(_jd_jst_midnight(d))
        b = _sun_longitude(_jd_jst_midnight(d + timedelta(days=1)))
        if (a - target_longitude) % 360 > 180 and (b - target_longitude) % 360 < 180:
            return d
    raise ValueError(f"黄経{target_longitude}の通過日が見つかりません: {year}-{month}")


def _nearest_kinoe_ne(d: date) -> date:
    i = kanshi_index(d)
    back, fwd = i, (60 - i) % 60
    return d - timedelta(days=back) if back <= fwd else d + timedelta(days=fwd)


def kyusei_day(d: date) -> int:
    starts = []
    for y in (d.year - 1, d.year, d.year + 1):
        starts.append((_nearest_kinoe_ne(crossing_date(y, 12, 270.0)), "yo"))
        starts.append((_nearest_kinoe_ne(crossing_date(y, 6, 90.0)), "in"))
    start, mode = max((s for s in starts if s[0] <= d), key=lambda s: s[0])
    k = (d - start).days % 9
    return k + 1 if mode == "yo" else 9 - k


def digital_root(n: int) -> int:
    return 0 if n == 0 else 1 + (n - 1) % 9


def numerology(d: date) -> int:
    n = sum(int(c) for c in d.strftime("%Y%m%d"))
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(c) for c in str(n))
    return n


def _relation(day_gogyo: str, star_gogyo: str):
    if day_gogyo == star_gogyo:
        return "比和", "日の気と星の気が同じ五行で重なり、流れが強まりやすい配置"
    if SOJO[star_gogyo] == day_gogyo:
        return "相生", f"星の{star_gogyo}が日の{day_gogyo}を生む、穏やかに後押しされる配置"
    if SOJO[day_gogyo] == star_gogyo:
        return "相生", f"日の{day_gogyo}が星の{star_gogyo}を生む、力が外へ広がる配置"
    return "相剋", "五行がぶつかり合う、波のある配置"


def lucky_days(d: date) -> list:
    ks = kanshi(d)
    month = setsu_month(d)
    days = []
    if TENSHA[month] == ks:
        days.append("天赦日")
    if ks[1] in ICHIRYU[month]:
        days.append("一粒万倍日")
    if ks == "己巳":
        days.append("己巳の日")
    elif ks[1] == "巳":
        days.append("巳の日")
    if ks[1] == "寅":
        days.append("寅の日")
    if ks == "甲子":
        days.append("甲子の日")
    return days


def koyomi(d: date) -> dict:
    ks = kanshi(d)
    star = kyusei_day(d)
    month = setsu_month(d)
    day_gogyo = KAN_GOGYO[kanshi_index(d) % 10]
    star_gogyo = KYUSEI_GOGYO[star]
    relation, relation_text = _relation(day_gogyo, star_gogyo)
    num = numerology(d)
    root = digital_root(num)
    return {
        "date": d.isoformat(),
        "month": d.month,
        "day": d.day,
        "mmdd": f"{d.month:02d}{d.day:02d}",
        "kanshi": ks,
        "kyusei": star,
        "kyusei_name": KYUSEI_NAMES[star],
        "kyusei_gogyo": star_gogyo,
        "day_gogyo": day_gogyo,
        "relation": relation,
        "relation_text": relation_text,
        "rokuyo": rokuyo(d),
        "setsu_month_name": f"{SETSU_BRANCHES[month]}月（{SETSU_NAMES[month]}〜）",
        "lucky_days": lucky_days(d),
        "numerology": num,
        "numerology_root": root,
        "lucky_digits": sorted({star % 10, root % 10, *GOGYO_DIGITS[day_gogyo]}),
    }


def koyomi_number_score(n: int, ko: dict) -> float:
    """ロト系の数字 n と暦の重なり（0〜1）"""
    s = 0.0
    if n % 10 in ko["lucky_digits"]:
        s += 1.0
    if digital_root(n) == ko["kyusei"]:
        s += 1.0
    if digital_root(n) == ko["numerology_root"]:
        s += 1.0
    if n in (ko["month"], ko["day"]):
        s += 0.5
    return s / 3.5


def koyomi_digit_score(g: int, position: int, digits: int, ko: dict) -> float:
    """ナンバーズの桁 position の数字 g と暦の重なり（0〜1）"""
    s = 0.5 if g in ko["lucky_digits"] else 0.0
    if g == ko["kyusei"] % 10:
        s += 0.2
    if g == ko["numerology_root"] % 10:
        s += 0.2
    if g == int(ko["mmdd"][-digits:][position]):
        s += 0.2
    return min(s, 1.0)
