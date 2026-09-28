"""無料の紹介記事（このノートの読み方）を note に投稿する

  python scripts/post_intro.py --dry-run   # 生成のみ（output/articles/intro.md）
  python scripts/post_intro.py             # 投稿
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import DATA_DIR, GAMES, OUTPUT_DIR
from src.content.compliance import assert_clean
from src.content.intro import build_intro
from src.data.fetcher import load_results
from src.predict.learning import _weights_before
from src.predict.store import load_state
from src.publishers.cover import generate_intro_cover
from src.utils.dates import now_jst
from src.utils.logger import get_logger

logger = get_logger("post_intro")
RECORD = DATA_DIR / "intro_post.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    totals, weights = {}, {}
    for key in ("loto6", "loto7", "numbers4", "numbers3"):
        results = load_results(GAMES[key])
        if not results:
            raise RuntimeError(f"{GAMES[key].name} のデータがありません。先に予想記事を1回生成してください")
        totals[key] = len(results)
        state = load_state(key)
        weeks = sorted(state.get("weeks", {}))
        weights[key] = state["weeks"][weeks[-1]]["after"] if weeks else _weights_before(state, "9999-99-99")

    title, body, hashtags = build_intro(totals, {k: weights[k] for k in ("loto6", "loto7", "numbers4")})
    assert_clean(title, body)

    cover = generate_intro_cover(OUTPUT_DIR / "images" / "intro.png")
    md_path = OUTPUT_DIR / "articles" / "intro.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {title}\n\n{body}\n\nハッシュタグ: {' '.join('#' + t for t in hashtags)}\n", encoding="utf-8")
    logger.info(f"記事を保存: {md_path}（{len(body)}字）")

    if args.dry_run:
        logger.info("dry-run のため投稿しません")
        return

    from src.publishers.note_publisher import NotePublisher

    url = NotePublisher().publish_free_article(title=title, content=body, cover_image_path=cover, hashtags=hashtags)
    RECORD.write_text(json.dumps({"url": url, "posted_at": now_jst().isoformat(timespec="seconds")},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"=== 投稿完了: {url} ===")


if __name__ == "__main__":
    main()
