from datetime import date

from scripts.post_column import MIN_INTERVAL_DAYS, posted_recently


def test_skips_when_posted_this_week():
    history = [{"topic": "myths", "posted_at": "2026-10-04T20:07:00+09:00"}]
    # 予備の実行（同日・翌日）では投稿しない
    assert posted_recently(history, date(2026, 10, 4)) is True
    assert posted_recently(history, date(2026, 10, 5)) is True


def test_posts_again_after_a_week():
    history = [{"topic": "myths", "posted_at": "2026-10-04T20:07:00+09:00"}]
    assert posted_recently(history, date(2026, 10, 11)) is False
    assert posted_recently(history, date(2026, 10, 4 + MIN_INTERVAL_DAYS)) is False


def test_empty_history():
    assert posted_recently([], date(2026, 10, 4)) is False


def test_uses_latest_entry_even_if_unsorted():
    history = [
        {"topic": "koyomi", "posted_at": "2026-10-04T22:12:00+09:00"},
        {"topic": "myths", "posted_at": "2026-09-27T20:00:00+09:00"},
    ]
    assert posted_recently(history, date(2026, 10, 6)) is True
