"""予想記事を生成して note に投稿する

  python scripts/run_post.py --series numbers --dry-run     # 生成のみ（output/articles に保存）
  python scripts/run_post.py --series loto6                 # 本番投稿
  python scripts/run_post.py --series loto7 --today 2026-09-16 --dry-run
"""

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import GAMES, OUTPUT_DIR, SERIES
from src.content.article import build_article
from src.content.compliance import assert_clean
from src.content.narrator import narrate
from src.data.fetcher import load_results, update_results
from src.pipeline import is_posted, prediction_record, prepare_game
from src.predict.store import save_prediction
from src.publishers.cover import generate_cover
from src.utils.dates import base_date, latest_draw_date, next_draw_date, now_jst, to_date
from src.utils.logger import get_logger

logger = get_logger("run_post")

LATEST_RETRY = 3
LATEST_RETRY_WAIT = 300


def _fetch_with_latest(game, now) -> list:
    """当日分の結果がまだ反映されていなければ少し待って再取得する"""
    base = now.date() if now.hour >= 20 else now.date() - timedelta(days=1)
    expected = latest_draw_date(game, base)
    results = update_results(game)
    for attempt in range(LATEST_RETRY):
        if to_date(results[-1]["date"]) >= expected:
            break
        logger.warning(
            f"{game.name}: 最新 {results[-1]['date']} < 期待 {expected}。{LATEST_RETRY_WAIT}秒後に再取得（{attempt + 1}/{LATEST_RETRY}）"
        )
        time.sleep(LATEST_RETRY_WAIT)
        results = update_results(game)
    return results


def _github_output(key: str, value: str):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True, choices=sorted(SERIES))
    ap.add_argument("--dry-run", action="store_true", help="生成のみで投稿しない（学習状態も保存しない）")
    ap.add_argument("--today", help="基準日 YYYY-MM-DD（既定: JST の今日）。この翌日以降の最初の抽せん回を対象にする")
    ap.add_argument("--no-fetch", action="store_true", help="保存済みの当せん番号データを使う")
    ap.add_argument("--force", action="store_true", help="投稿済みの回でも再投稿する")
    args = ap.parse_args()

    series = SERIES[args.series]
    now = now_jst()
    # 定時実行の遅れ（翌未明にずれ込むこと）があっても予定どおりの回を対象にする
    today = date.fromisoformat(args.today) if args.today else base_date(now)
    persist = not args.dry_run

    results = {}
    for key in series.games:
        game = GAMES[key]
        if args.no_fetch:
            results[key] = load_results(game)
        elif args.today or args.dry_run:
            results[key] = update_results(game)
        else:
            results[key] = _fetch_with_latest(game, now)

    target = next_draw_date(GAMES[series.games[0]], today)
    logger.info(f"=== {series.title_name} {target} 抽せん分の記事を作成 ===")
    ctxs = [prepare_game(GAMES[key], results[key], target, persist) for key in series.games]
    logger.info("対象: " + " / ".join(f"{c['game'].name} 第{c['draw']}回" for c in ctxs))

    if not args.dry_run and not args.force and all(is_posted(c) for c in ctxs):
        logger.info("この回は投稿済みのためスキップします（--force で再投稿）")
        return

    narr = narrate(series, ctxs)
    article = build_article(series, ctxs, narr)
    assert_clean(article.title, article.teaser, article.paid)

    stem = f"{series.key}_{target.isoformat()}"
    cover = generate_cover(series, ctxs[0]["draw"], target, ctxs[0]["ko"], OUTPUT_DIR / "images" / f"{stem}.png")
    md_path = OUTPUT_DIR / "articles" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(article.to_markdown(), encoding="utf-8")
    logger.info(f"記事を保存: {md_path}（無料 {len(article.teaser)}字／有料 {len(article.paid)}字）")

    if args.dry_run:
        logger.info("dry-run のため投稿しません")
        return

    from src.publishers.note_publisher import NotePublisher

    url = NotePublisher().publish_article(
        title=article.title,
        teaser_content=article.teaser,
        paid_content=article.paid,
        price=series.price,
        cover_image_path=cover,
        hashtags=article.hashtags,
    )
    posted_at = now_jst().isoformat(timespec="seconds")
    for c in ctxs:
        save_prediction(c["game"].key, c["draw"], prediction_record(c, series.key, url, posted_at))
    _github_output("note_url", url)
    logger.info(f"=== 投稿完了: {url} ===")


if __name__ == "__main__":
    main()
