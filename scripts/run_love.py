"""恋愛占い記事を note に投稿する

  python scripts/run_love.py --product weekly --dry-run        # 12星座分を生成only
  python scripts/run_love.py --product summary                  # まとめ1本を投稿
  python scripts/run_love.py --product intensive --sign aries   # 1星座だけ投稿
  python scripts/run_love.py --product weekly --today 2026-10-19 --dry-run

隔週の商品（intensive）は、ISO週番号が偶数の週だけ実行する（--ignore-biweekly で無視）。
"""

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.astro.love import all_signs_data, period_data
from src.astro.signs import BY_EN, ZODIAC_SIGNS
from src.config import DATA_DIR, OUTPUT_DIR
from src.content import love_article
from src.content.compliance import assert_clean
from src.content.love_narrator import narrate
from src.love_config import BRAND, POST_INTERVAL, PRODUCTS
from src.publishers.cover import generate_ranking_cover, generate_sign_cover
from src.utils.dates import base_date, now_jst, week_start
from src.utils.logger import get_logger

logger = get_logger("run_love")
LEGACY_RECORD = DATA_DIR / "love_posts.json"


def record_path(product_key: str):
    """投稿記録は商品ごとに別ファイル（同時に動く別商品の実行と、コミット時に記録を消し合わないため）"""
    return DATA_DIR / f"love_posts_{product_key}.json"
HEADLINES = {"daily": "今日の恋愛運", "weekly": "週間恋愛運",
             "intensive": "2週間の恋愛集中鑑定", "summary": "12星座の恋愛運"}


def load_record(product_key: str) -> list:
    path = record_path(product_key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if LEGACY_RECORD.exists():  # 旧形式（全商品で1ファイル）からの移行
        legacy = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
        return [r for r in legacy if r.get("product") == product_key]
    return []


def save_record(product_key: str, record: list) -> None:
    path = record_path(product_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def period_for(product_key: str, today: date) -> tuple:
    """商品ごとの対象期間"""
    if product_key == "daily":
        # 夕方に投稿して、翌日の運勢を届ける
        start = today + timedelta(days=1)
        return start, start
    if product_key == "weekly":
        # 日曜に翌週分を出す（月曜に実行した場合はその週）
        start = week_start(today + timedelta(days=1))
        return start, start + timedelta(days=6)
    if product_key == "intensive":
        start = week_start(today) + timedelta(days=7)  # 翌週からの2週間
        return start, start + timedelta(days=13)
    start = today
    return start, start + timedelta(days=PRODUCTS["summary"].period_days - 1)


def already_posted(record: list, product: str, start: date, sign_en: str) -> bool:
    return any(r["product"] == product and r["period_start"] == start.isoformat()
               and r.get("sign") == sign_en and r.get("url") for r in record)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True, choices=sorted(PRODUCTS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="基準日 YYYY-MM-DD（既定: JST の今日、定時実行の遅れを考慮）")
    ap.add_argument("--sign", help="星座を1つだけ（例: aries）")
    ap.add_argument("--force", action="store_true", help="投稿済みでも投稿する")
    ap.add_argument("--ignore-biweekly", action="store_true", help="隔週判定を無視する")
    args = ap.parse_args()

    product = PRODUCTS[args.product]
    today = date.fromisoformat(args.today) if args.today else base_date(now_jst())
    start, end = period_for(product.key, today)

    if product.key == "intensive" and not args.ignore_biweekly and start.isocalendar()[1] % 2 != 0:
        logger.info(f"今週は隔週の対象外のためスキップします（ISO週 {start.isocalendar()[1]}）")
        return

    record = load_record(product.key)
    logger.info(f"=== {product.name}（{product.price}円）対象期間 {start} 〜 {end} ===")

    targets = []
    if product.per_sign:
        signs = [BY_EN[args.sign]] if args.sign else ZODIAC_SIGNS
        for sign in signs:
            data = period_data(sign, start, end)
            narr = narrate(product.key, data=data)
            article = getattr(love_article, product.builder)(data, BRAND, narr)
            targets.append((sign, article))
    else:
        rows = all_signs_data(start, end)
        narr = narrate("summary", rows=rows, start=start, end=end)
        article = love_article.build_summary(rows, start, end, BRAND, narr)
        targets.append((None, article))

    posted, failed = 0, []
    for index, (sign, article) in enumerate(targets):
        sign_en = sign["en"] if sign else "all"
        assert_clean(article.title, article.teaser, article.paid)

        stem = f"{product.key}_{start.isoformat()}_{sign_en}"
        md_path = OUTPUT_DIR / "articles" / f"{stem}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(article.to_markdown(), encoding="utf-8")

        if sign:
            cover = generate_sign_cover(sign, HEADLINES[product.key],
                                        f"{start.month}/{start.day}〜{end.month}/{end.day}",
                                        OUTPUT_DIR / "images" / f"{stem}.png")
        else:
            cover = generate_ranking_cover("12星座の恋愛運ランキング",
                                           f"{start.month}/{start.day}〜{end.month}/{end.day}",
                                           OUTPUT_DIR / "images" / f"{stem}.png")

        if args.dry_run:
            logger.info(f"[{index + 1}/{len(targets)}] 生成: {md_path.name}（無料 {len(article.teaser)}字／有料 {len(article.paid)}字）")
            continue

        if not args.force and already_posted(record, product.key, start, sign_en):
            logger.info(f"[{index + 1}/{len(targets)}] 投稿済みのためスキップ: {sign_en}")
            continue

        from src.publishers.note_publisher import NotePublisher

        try:
            url = NotePublisher().publish_article(
                title=article.title, teaser_content=article.teaser, paid_content=article.paid,
                price=product.price, cover_image_path=cover, hashtags=article.hashtags,
            )
        except Exception as e:
            # note は短時間の連続公開を制限するらしく、1本失敗すると後続も失敗して下書きが溜まる。
            # そのため1本目の失敗で打ち切り、残りは約2時間後の予備の実行（未投稿分だけ投稿）に任せる。
            failed.append(sign_en)
            failed += [t[0]["en"] for t in targets[index + 1:]
                       if t[0] and not already_posted(record, product.key, start, t[0]["en"])]
            logger.error(f"[{index + 1}/{len(targets)}] 投稿失敗（{sign_en}）: {str(e).splitlines()[0][:160]}")
            logger.error("連続公開の制限にかかった可能性があるため、この回は打ち切ります")
            break
        record.append({"product": product.key, "period_start": start.isoformat(), "sign": sign_en,
                       "price": product.price, "url": url, "posted_at": now_jst().isoformat(timespec="seconds")})
        save_record(product.key, record)
        posted += 1
        logger.info(f"[{index + 1}/{len(targets)}] 投稿完了: {url}")
        if index < len(targets) - 1:
            time.sleep(POST_INTERVAL)

    if args.dry_run:
        logger.info(f"dry-run のため投稿しません（{len(targets)}本を生成）")
    else:
        logger.info(f"=== 完了: {posted}本を投稿 ===")
        if failed:
            logger.error(f"投稿できなかった星座: {'、'.join(failed)}（同じコマンドで再実行すると未投稿分だけ投稿します）")
            sys.exit(1)


if __name__ == "__main__":
    main()
