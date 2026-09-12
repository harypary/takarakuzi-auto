from datetime import date, timedelta

from src.koyomi import crossing_date, kanshi, koyomi, kyusei_day, rokuyo, setsu_month


def test_kanshi_reference_day():
    assert kanshi(date(2000, 1, 1)) == "戊午"
    assert kanshi(date(2000, 1, 2)) == "己未"


def test_rokuyo_lunar_new_year_is_sensho():
    # 2026年の旧正月は 2/17（旧暦1月1日は先勝）
    assert rokuyo(date(2026, 2, 17)) == "先勝"


def test_setsu_month_boundaries():
    assert setsu_month(date(2026, 1, 20)) == 11  # 丑月
    assert setsu_month(date(2026, 2, 10)) == 0  # 寅月（立春後）
    assert setsu_month(date(2026, 9, 13)) == 7  # 酉月（白露後）


def test_summer_solstice_2026():
    assert crossing_date(2026, 6, 90.0) == date(2026, 6, 21)


def test_kyusei_moves_one_step_per_day():
    d = date(2026, 3, 1)
    for _ in range(90):
        a, b = kyusei_day(d), kyusei_day(d + timedelta(days=1))
        assert (b - a) % 9 == 1  # 3〜5月は陽遁で1ずつ増える
        d += timedelta(days=1)


def test_koyomi_fields():
    ko = koyomi(date(2026, 9, 14))
    assert 1 <= ko["kyusei"] <= 9
    assert ko["rokuyo"] in ("大安", "赤口", "先勝", "友引", "先負", "仏滅")
    assert all(0 <= g <= 9 for g in ko["lucky_digits"])
