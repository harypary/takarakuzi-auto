"""ジャンボ宝くじの無料記事（買う日を暦で選ぶ）を note に投稿する

  python scripts/post_jumbo.py --dry-run   # 生成のみ（output/articles/jumbo_*.md）
  python scripts/post_jumbo.py             # 投稿

商品情報は公式サイト（takarakuji-official.jp）で確認した値を JUMBO に置く。
新しいジャンボのたびに JUMBO を差し替えて実行する。
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import DATA_DIR, OUTPUT_DIR
from src.content.compliance import assert_clean
from src.content.jumbo import Jumbo, build_jumbo
from src.publishers.cover import generate_jumbo_cover
from src.utils.dates import now_jst
from src.utils.logger import get_logger

logger = get_logger("post_jumbo")

# 2026-09-28 に宝くじ公式サイトで確認
JUMBO = Jumbo(
    name="ハロウィンジャンボ宝くじ",
    sale_start=date(2026, 9, 16),
    sale_end=date(2026, 10, 16),
    draw_date=date(2026, 10, 26),
    payout_start=date(2026, 11, 2),
    price=300,
    first_prize="2億円（12本）",
    first_with_adjacent="4億円",
    second_prize="1億円（24本）",
    odds="1,000万分の1（12本／1億2,000万枚・12ユニット）",
    mini_name="ハロウィンジャンボミニ",
    mini_first="2,000万円（50本）",
    mini_with_adjacent="4,000万円",
    online=True,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="基準日 YYYY-MM-DD（既定: JST の今日）")
    args = ap.parse_args()

    today = date.fromisoformat(args.today) if args.today else now_jst().date()
    if today > JUMBO.sale_end:
        raise SystemExit(f"{JUMBO.name} の発売は {JUMBO.sale_end} に終了しています。JUMBO を次の商品に差し替えてください")

    title, body, hashtags = build_jumbo(JUMBO, today)
    assert_clean(title, body)

    cover = generate_jumbo_cover(JUMBO.name, JUMBO.sale_end, JUMBO.draw_date, OUTPUT_DIR / "images" / "jumbo.png")
    stem = f"jumbo_{today.isoformat()}"
    md_path = OUTPUT_DIR / "articles" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {title}\n\n{body}\n\nハッシュタグ: {' '.join('#' + t for t in hashtags)}\n", encoding="utf-8")
    logger.info(f"記事を保存: {md_path}（{len(body)}字）")

    if args.dry_run:
        logger.info("dry-run のため投稿しません")
        return

    from src.publishers.note_publisher import NotePublisher

    url = NotePublisher().publish_free_article(title=title, content=body, cover_image_path=cover, hashtags=hashtags)
    record = DATA_DIR / "jumbo_posts.json"
    posts = json.loads(record.read_text(encoding="utf-8")) if record.exists() else []
    posts.append({"name": JUMBO.name, "url": url, "posted_at": now_jst().isoformat(timespec="seconds")})
    record.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"=== 投稿完了: {url} ===")


if __name__ == "__main__":
    main()
