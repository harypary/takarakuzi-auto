"""恋愛占いアカウントの設定（商品・価格・投稿スケジュール）"""

from dataclasses import dataclass

BRAND = "ふたりの星図"  # 記事タイトル末尾に入る名前。アカウント名に合わせて変更する
NOTE_URLNAME = ""  # 新しい note アカウントの ID（例: koi_hoshi）。セッション設定後に記入


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    price: int
    per_sign: bool          # True = 12星座それぞれ1本、False = 全星座まとめ1本
    period_days: int        # 対象期間の長さ
    builder: str            # src.content.love_article の関数名


PRODUCTS = {
    "weekly": Product("weekly", "週間恋愛運", 980, True, 7, "build_weekly"),
    "intensive": Product("intensive", "2週間の恋愛集中鑑定", 1980, True, 14, "build_intensive"),
    "summary": Product("summary", "12星座の恋愛運ランキング", 500, False, 3, "build_summary"),
}

# 投稿間隔（秒）。12本連続で投稿するときの Bot 検出対策
POST_INTERVAL = 40
