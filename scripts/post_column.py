"""無料コラムを note に投稿する（週1回・4種類の持ち回り）

  python scripts/post_column.py --dry-run            # 次に出す種類を自動で選んで生成
  python scripts/post_column.py --topic koyomi       # 種類を指定
  python scripts/post_column.py                      # 投稿
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
from src.content.column import TOPICS, build, choose_topic
from src.content.compliance import assert_clean
from src.data.fetcher import load_results, update_results
from src.publishers.cover import generate_column_cover
from src.utils.dates import now_jst, to_date
from src.utils.logger import get_logger

logger = get_logger("post_column")
RECORD = DATA_DIR / "column_posts.json"
GAME_KEYS = ("loto6", "loto7", "numbers4", "numbers3")
MIN_INTERVAL_DAYS = 5  # 週1回なので、5日以内の再投稿はしない


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topic", choices=TOPICS, help="省略時は直近に使っていない種類を自動で選ぶ")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--force", action="store_true", help="同じ週にすでに投稿していても投稿する")
    args = ap.parse_args()

    today = now_jst().date()
    history = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else []

    # 予備の実行で2本目を出さないよう、同じ週に投稿済みならスキップする
    if history and not args.force and not args.dry_run:
        last = to_date(history[-1]["posted_at"][:10])
        if (today - last).days < MIN_INTERVAL_DAYS:
            logger.info(f"{last} にコラムを投稿済みのためスキップします（--force で投稿）")
            return

    topic = args.topic or choose_topic(today, history)
    logger.info(f"今回のコラム: {topic}")

    for key in GAME_KEYS:
        if not args.no_fetch:
            update_results(GAMES[key])

    ctx = {
        "today": today,
        "loto": {k: analyze_loto(GAMES[k], load_results(GAMES[k])) for k in ("loto6", "loto7")},
        "numbers": {k: analyze_numbers(GAMES[k], load_results(GAMES[k])) for k in ("numbers4", "numbers3")},
    }
    title, body, hashtags = build(topic, ctx)
    assert_clean(title, body)

    cover = generate_column_cover(OUTPUT_DIR / "images" / f"column_{topic}.png", topic)
    md_path = OUTPUT_DIR / "articles" / f"column_{topic}_{today.isoformat()}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {title}\n\n{body}\n\nハッシュタグ: {' '.join('#' + t for t in hashtags)}\n", encoding="utf-8")
    logger.info(f"記事を保存: {md_path}（{len(body)}字）")

    if args.dry_run:
        logger.info("dry-run のため投稿しません")
        return

    from src.publishers.note_publisher import NotePublisher

    url = NotePublisher().publish_free_article(title=title, content=body, cover_image_path=cover, hashtags=hashtags)
    history.append({"topic": topic, "title": title, "url": url,
                    "posted_at": now_jst().isoformat(timespec="seconds")})
    RECORD.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"=== 投稿完了: {url} ===")


if __name__ == "__main__":
    main()
