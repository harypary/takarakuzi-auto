"""無料コラム（よくある誤解をデータで確かめる）を note に投稿する

  python scripts/post_column.py --dry-run
  python scripts/post_column.py
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.analysis.loto import analyze_loto
from src.analysis.numbers import analyze_numbers
from src.config import DATA_DIR, GAMES, OUTPUT_DIR
from src.content.column import build_column
from src.content.compliance import assert_clean
from src.data.fetcher import load_results
from src.publishers.cover import generate_column_cover
from src.utils.dates import now_jst
from src.utils.logger import get_logger

logger = get_logger("post_column")
RECORD = DATA_DIR / "column_posts.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    loto = {k: analyze_loto(GAMES[k], load_results(GAMES[k])) for k in ("loto6", "loto7")}
    numbers = {k: analyze_numbers(GAMES[k], load_results(GAMES[k])) for k in ("numbers4", "numbers3")}
    title, body, hashtags = build_column(loto, numbers)
    assert_clean(title, body)

    cover = generate_column_cover(OUTPUT_DIR / "images" / "column.png")
    stem = f"column_{now_jst().date().isoformat()}"
    md_path = OUTPUT_DIR / "articles" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {title}\n\n{body}\n\nハッシュタグ: {' '.join('#' + t for t in hashtags)}\n", encoding="utf-8")
    logger.info(f"記事を保存: {md_path}（{len(body)}字）")

    if args.dry_run:
        logger.info("dry-run のため投稿しません")
        return

    from src.publishers.note_publisher import NotePublisher

    url = NotePublisher().publish_free_article(title=title, content=body, cover_image_path=cover, hashtags=hashtags)
    posts = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else []
    posts.append({"title": title, "url": url, "posted_at": now_jst().isoformat(timespec="seconds")})
    RECORD.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"=== 投稿完了: {url} ===")


if __name__ == "__main__":
    main()
