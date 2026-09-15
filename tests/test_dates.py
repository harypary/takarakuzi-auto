from datetime import date, datetime

from src.config import GAMES
from src.utils.dates import JST, base_date, next_draw_date


def test_delayed_sunday_run_still_targets_monday_draw():
    game = GAMES["numbers4"]
    for hour, minute in ((21, 37), (23, 59)):
        assert next_draw_date(game, base_date(datetime(2026, 9, 13, hour, minute, tzinfo=JST))) == date(2026, 9, 14)
    # 翌未明（実際に起きた遅れ）でも月曜の回を狙う
    assert next_draw_date(game, base_date(datetime(2026, 9, 14, 1, 33, tzinfo=JST))) == date(2026, 9, 14)
    assert next_draw_date(game, base_date(datetime(2026, 9, 14, 5, 30, tzinfo=JST))) == date(2026, 9, 14)


def test_evening_run_targets_next_day():
    game = GAMES["numbers4"]
    assert next_draw_date(game, base_date(datetime(2026, 9, 14, 21, 37, tzinfo=JST))) == date(2026, 9, 15)


def test_loto_schedules():
    loto6, loto7 = GAMES["loto6"], GAMES["loto7"]
    # 土曜21時 → 月曜、遅れて日曜未明でも月曜
    assert next_draw_date(loto6, base_date(datetime(2026, 9, 19, 21, 7, tzinfo=JST))) == date(2026, 9, 21)
    assert next_draw_date(loto6, base_date(datetime(2026, 9, 20, 3, 0, tzinfo=JST))) == date(2026, 9, 21)
    # 水曜21時 → 金曜
    assert next_draw_date(loto7, base_date(datetime(2026, 9, 23, 21, 7, tzinfo=JST))) == date(2026, 9, 25)
