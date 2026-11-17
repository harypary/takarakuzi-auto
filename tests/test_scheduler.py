from datetime import date, datetime

from scripts.run_scheduler import due_tasks, is_intensive_week, plan
from src.love_config import MAX_PUBLISH_PER_DAY, MAX_PUBLISH_PER_HOUR


def _count(tasks, product):
    return sum(1 for t in tasks if t.product == product)


def test_daily_today_and_tomorrow_until_evening():
    tasks = due_tasks(datetime(2026, 11, 18, 14, 0))  # 水曜の昼
    days = sorted({t.start for t in tasks if t.product == "daily"})
    assert days == [date(2026, 11, 18), date(2026, 11, 19)]
    night = due_tasks(datetime(2026, 11, 18, 22, 0))
    assert sorted({t.start for t in night if t.product == "daily"}) == [date(2026, 11, 19)]


def test_weekly_is_posted_ahead_from_tuesday():
    tuesday = due_tasks(datetime(2026, 11, 17, 10, 0))
    weekly_starts = {t.start for t in tuesday if t.product == "weekly"}
    assert date(2026, 11, 23) in weekly_starts       # 翌週分を前倒し
    assert date(2026, 11, 16) in weekly_starts       # 今週分も火曜までは遅れて出せる
    wednesday = due_tasks(datetime(2026, 11, 18, 10, 0))
    assert {t.start for t in wednesday if t.product == "weekly"} == {date(2026, 11, 23)}
    monday = due_tasks(datetime(2026, 11, 23, 10, 0))
    assert {t.start for t in monday if t.product == "weekly"} == {date(2026, 11, 23)}


def test_summary_on_tuesday_and_friday():
    monday = due_tasks(datetime(2026, 11, 16, 10, 0))
    assert [t.start for t in monday if t.product == "summary"] == [date(2026, 11, 17)]
    wednesday = due_tasks(datetime(2026, 11, 18, 10, 0))
    assert _count(wednesday, "summary") == 0


def test_intensive_only_for_even_iso_weeks():
    assert is_intensive_week(date(2026, 11, 9))       # ISO 46
    assert not is_intensive_week(date(2026, 11, 16))  # ISO 47
    tasks = due_tasks(datetime(2026, 11, 18, 10, 0))  # 11/23（ISO 48）開始の1週間前以内
    assert {t.start for t in tasks if t.product == "intensive"} == {date(2026, 11, 23)}
    assert _count(tasks, "intensive") == 12


def test_plan_puts_daily_first_and_respects_hourly_cap():
    tasks = due_tasks(datetime(2026, 11, 18, 10, 0))
    chosen = plan(tasks, day_used=0, hour_used=0)
    assert len(chosen) == MAX_PUBLISH_PER_HOUR
    assert all(t.product == "daily" for t in chosen)
    assert chosen[0].start == date(2026, 11, 18)       # 今日の分が先


def test_plan_reserves_slots_for_daily():
    # 明日の毎日分12本が未投稿で、24時間で既に3本使っている → 残り12枠は毎日分に確保し、週間は出さない
    tasks = [t for t in due_tasks(datetime(2026, 11, 18, 22, 0)) if t.product in ("daily", "weekly")]
    chosen = plan(tasks, day_used=3, hour_used=0)
    assert all(t.product == "daily" for t in chosen)


def test_plan_uses_leftover_for_weekly_when_daily_done():
    tasks = [t for t in due_tasks(datetime(2026, 11, 18, 22, 0)) if t.product == "weekly"]
    chosen = plan(tasks, day_used=12, hour_used=0)
    assert len(chosen) == MAX_PUBLISH_PER_DAY - 12
    assert all(t.product == "weekly" for t in chosen)


def test_plan_stops_at_daily_cap():
    tasks = due_tasks(datetime(2026, 11, 18, 10, 0))
    assert plan(tasks, day_used=MAX_PUBLISH_PER_DAY, hour_used=0) == []
