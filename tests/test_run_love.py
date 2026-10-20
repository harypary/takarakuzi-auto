import io
import json
from datetime import timedelta

import scripts.run_love as run_love
from src.utils.dates import now_jst


def _fake_urlopen(rows):
    def fake(req, timeout=30):
        return io.BytesIO(json.dumps({"data": {"contents": rows}}).encode("utf-8"))
    return fake


def test_counts_only_posts_within_the_last_hour(monkeypatch):
    now = now_jst()
    rows = [{"publishAt": (now - timedelta(minutes=m)).isoformat()} for m in (5, 20, 40, 59, 61, 120)]
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(rows))
    assert run_love.recent_publish_count() == 4


def test_returns_zero_when_api_fails(monkeypatch):
    def broken(req, timeout=30):
        raise OSError("network down")
    monkeypatch.setattr("urllib.request.urlopen", broken)
    assert run_love.recent_publish_count() == 0


def test_period_for_daily_and_weekly():
    from datetime import date
    # 日曜に実行した週間は翌週（月〜日）
    assert run_love.period_for("weekly", date(2026, 10, 25)) == (date(2026, 10, 26), date(2026, 11, 1))
