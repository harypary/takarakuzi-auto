"""日付ユーティリティ（JST・週の計算）"""

from datetime import date, datetime, timedelta, timezone

from src.config import WEEKDAY_JA

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def base_date(now: datetime) -> date:
    """記事の基準日。GitHub Actions の定時実行は数時間遅れることがあるため、
    12時間さかのぼった日付を「今日」とみなす（夕方の予定が翌未明にずれても対象期間を外さない）。"""
    return (now - timedelta(hours=12)).date()


def to_date(value) -> date:
    return date.fromisoformat(value) if isinstance(value, str) else value


def week_start(d: date) -> date:
    """月曜始まりの週の月曜日"""
    return d - timedelta(days=d.weekday())


def md_wd(d) -> str:
    """10/19(月)"""
    d = to_date(d)
    return f"{d.month}/{d.day}({WEEKDAY_JA[d.weekday()]})"


def ymd_ja(d) -> str:
    """2026年10月19日（月）"""
    d = to_date(d)
    return f"{d.year}年{d.month}月{d.day}日（{WEEKDAY_JA[d.weekday()]}）"
