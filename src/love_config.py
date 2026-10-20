"""恋愛占いアカウントの設定（商品・価格・投稿スケジュール）"""

from dataclasses import dataclass

BRAND = "恋の星読み"  # 記事タイトル末尾とカバーに入る名前（表示名: 恋の星読み｜12星座の恋愛占い）
NOTE_URLNAME = "koi_hoshiyomi"  # note アカウントの ID（https://note.com/koi_hoshiyomi）


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    price: int
    per_sign: bool          # True = 12星座それぞれ1本、False = 全星座まとめ1本
    period_days: int        # 対象期間の長さ
    builder: str            # src.content.love_article の関数名


PRODUCTS = {
    "daily": Product("daily", "今日の恋愛運", 300, True, 1, "build_daily"),
    "weekly": Product("weekly", "週間恋愛運", 980, True, 7, "build_weekly"),
    "intensive": Product("intensive", "2週間の恋愛集中鑑定", 1980, True, 14, "build_intensive"),
    "summary": Product("summary", "12星座の恋愛運ランキング", 500, False, 3, "build_summary"),
}

# 投稿間隔（秒）。12本連続で投稿するときの Bot 検出対策
POST_INTERVAL = 120  # 短い間隔だと5〜6本目あたりから公開が確定しなくなる（note の連続公開の制限とみられる）

# note は短時間の連続公開を制限する。実測では6本までは公開でき、7本目で確定しなくなった。
# 投稿前に「直近1時間に公開した本数」を数え、この本数に達したらその回は止めて次の実行に回す。
MAX_PUBLISH_PER_HOUR = 6
