from datetime import date

from src.koyomi import koyomi
from src.kyureki import lunar_month_day, rokuyo, shuo_date_on_or_before


def test_lunar_new_year_2026_is_sensho():
    # 旧暦1月1日（2026年の旧正月は2/17）は先勝
    assert lunar_month_day(date(2026, 2, 17)) == (1, 1)
    assert rokuyo(date(2026, 2, 17)) == "先勝"


def test_matches_official_lucky_day_calendar_2026_10():
    # 宝くじ公式サイトの吉日カレンダー（ハロウィンジャンボ）に掲載の大安
    for day in (2, 8, 13):
        assert rokuyo(date(2026, 10, day)) == "大安", day
    # 中国暦基準だとずれる日（朔が日本時間の深夜）
    assert rokuyo(date(2026, 10, 14)) != "大安"


def test_shuo_is_monotonic_and_within_a_month():
    d = date(2026, 1, 1)
    while d < date(2027, 1, 1):
        shuo = shuo_date_on_or_before(d)
        assert 0 <= (d - shuo).days <= 30
        d = d.replace(day=15) if d.day == 1 else (d.replace(day=1, month=d.month % 12 + 1)
                                                  if d.month < 12 else date(2027, 1, 1))


def test_koyomi_uses_new_rokuyo():
    assert koyomi(date(2026, 10, 13))["rokuyo"] == "大安"
