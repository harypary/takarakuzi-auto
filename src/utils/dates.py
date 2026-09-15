"""日付ユーティリティ（JST・抽せん日計算）"""

from datetime import date, datetime, timedelta, timezone

from src.config import NO_DRAW_MMDD, WEEKDAY_JA, Game

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def base_date(now: datetime) -> date:
    """記事の基準日。GitHub Actions の定時実行は数時間遅れることがあるため、
    12時間さかのぼった日付を「今日」とみなす（21時台の予定が翌未明に動いても狙いの回を外さない）。"""
    return (now - timedelta(hours=12)).date()


def to_date(value) -> date:
    return date.fromisoformat(value) if isinstance(value, str) else value


def week_start(d: date) -> date:
    """月曜始まりの週の月曜日"""
    return d - timedelta(days=d.weekday())


def md_wd(d) -> str:
    """9/14(月)"""
    d = to_date(d)
    return f"{d.month}/{d.day}({WEEKDAY_JA[d.weekday()]})"


def ymd_ja(d) -> str:
    """2026年9月14日（月）"""
    d = to_date(d)
    return f"{d.year}年{d.month}月{d.day}日（{WEEKDAY_JA[d.weekday()]}）"


def is_draw_day(game: Game, d: date) -> bool:
    return d.weekday() in game.draw_weekdays and (d.month, d.day) not in NO_DRAW_MMDD


def next_draw_date(game: Game, after: date) -> date:
    """after より後（翌日以降）で最初の抽せん日"""
    d = after + timedelta(days=1)
    while not is_draw_day(game, d):
        d += timedelta(days=1)
    return d


def latest_draw_date(game: Game, on_or_before: date) -> date:
    d = on_or_before
    while not is_draw_day(game, d):
        d -= timedelta(days=1)
    return d


def draw_number_for(game: Game, last_draw: int, last_date: date, target: date) -> int:
    """既知の最新回から、target 抽せん日の回号を数える"""
    n, d = last_draw, last_date
    while d < target:
        d += timedelta(days=1)
        if is_draw_day(game, d):
            n += 1
    return n
