"""投稿の予定表（スケジューラ）

note には「1時間に6本」「1日におよそ16本」の公開上限がある。
毎日12本＋週間12本が同じ日に重なると上限を超え、翌日の毎日投稿まで欠けてしまう。
そこで2時間おきに起動し、その時点で出すべき記事を優先順に並べて、枠の範囲で少しずつ出す。

  優先順：毎日（今日・明日分） → ランキング → 週間 → 集中鑑定（同じ商品の中は締め切りが早い順）
  週間・集中鑑定は、まだ出ていない毎日分の枠を残したうえで、空いた枠だけを使う。

  python scripts/run_scheduler.py --dry-run   # 今出す予定の記事と残り枠を表示するだけ
  python scripts/run_scheduler.py             # 投稿する
"""

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from scripts.run_love import HEADLINES, already_posted, load_record, recent_publish_count, save_record
from src.astro.love import all_signs_data, period_data
from src.astro.signs import ZODIAC_SIGNS
from src.config import OUTPUT_DIR
from src.content import love_article
from src.content.compliance import assert_clean
from src.content.love_narrator import narrate
from src.love_config import BRAND, MAX_PUBLISH_PER_DAY, MAX_PUBLISH_PER_HOUR, POST_INTERVAL, PRODUCTS
from src.publishers.cover import generate_ranking_cover, generate_sign_cover
from src.utils.dates import now_jst, week_start
from src.utils.logger import get_logger

logger = get_logger("run_scheduler")

PRODUCT_ORDER = {"daily": 0, "summary": 1, "weekly": 2, "intensive": 3}
SIGN_ORDER = {s["en"]: i for i, s in enumerate(ZODIAC_SIGNS)}
TODAY_DAILY_UNTIL_HOUR = 21  # 今日の分の毎日投稿は、この時刻を過ぎたら出さない（読まれる時間がない）


@dataclass(frozen=True)
class Task:
    product: str
    start: date
    end: date
    sign: Optional[dict]
    deadline: date

    @property
    def sign_en(self) -> str:
        return self.sign["en"] if self.sign else "all"

    def label(self) -> str:
        name = self.sign["name"] if self.sign else "12星座"
        return f"{PRODUCTS[self.product].name}（{self.start.month}/{self.start.day}〜）{name}"


def is_intensive_week(monday: date) -> bool:
    """集中鑑定は、ISO週番号が偶数の週に始まる2週間を扱う"""
    return monday.isocalendar()[1] % 2 == 0


def _per_sign(product: str, start: date, deadline: date) -> list:
    end = start + timedelta(days=PRODUCTS[product].period_days - 1)
    return [Task(product, start, end, sign, deadline) for sign in ZODIAC_SIGNS]


def due_tasks(now: datetime) -> list:
    """いま出してよい記事（投稿済みかどうかは見ない）"""
    today = now.date()
    tasks = []

    # 毎日：明日の分。今日の分も、出ていなければ夜までは出す
    days = [today + timedelta(days=1)]
    if now.hour < TODAY_DAILY_UNTIL_HOUR:
        days.insert(0, today)
    for day in days:
        tasks += _per_sign("daily", day, day)

    # ランキング：火曜・金曜に始まる3日間。前日から当日中に出す
    for day in (today, today + timedelta(days=1)):
        if day.weekday() in (1, 4):
            end = day + timedelta(days=PRODUCTS["summary"].period_days - 1)
            tasks.append(Task("summary", day, end, None, day))

    # 週間：翌週分を火曜から前倒しで出す。今週分も、火曜までなら遅れて出す
    this_monday = week_start(today)
    next_monday = this_monday + timedelta(days=7)
    if today.weekday() >= 1:
        tasks += _per_sign("weekly", next_monday, next_monday)
    if today.weekday() <= 1:
        tasks += _per_sign("weekly", this_monday, this_monday)

    # 集中鑑定：開始の1週間前から、開始後2日まで
    for monday in (this_monday, next_monday):
        if is_intensive_week(monday) and monday - timedelta(days=7) <= today <= monday + timedelta(days=2):
            tasks += _per_sign("intensive", monday, monday)
    return tasks


def sort_key(task: Task):
    return (PRODUCT_ORDER[task.product] > 0, task.deadline, PRODUCT_ORDER[task.product],
            SIGN_ORDER.get(task.sign_en, 99))


def plan(pending: list, day_used: int, hour_used: int) -> list:
    """今回の実行で出す記事。まだ出ていない毎日分の枠は、ほかの商品に使わせない"""
    pending = sorted(pending, key=sort_key)
    daily_left = sum(1 for t in pending if t.product == "daily")
    chosen = []
    for task in pending:
        if hour_used + len(chosen) >= MAX_PUBLISH_PER_HOUR or day_used + len(chosen) >= MAX_PUBLISH_PER_DAY:
            break
        if task.product == "daily":
            chosen.append(task)
            daily_left -= 1
            continue
        free_after_daily = MAX_PUBLISH_PER_DAY - day_used - len(chosen) - daily_left
        if free_after_daily > 0:
            chosen.append(task)
    return chosen


def make_article(task: Task):
    product = PRODUCTS[task.product]
    stem = f"{task.product}_{task.start.isoformat()}_{task.sign_en}"
    period_text = f"{task.start.month}/{task.start.day}〜{task.end.month}/{task.end.day}"
    if product.per_sign:
        data = period_data(task.sign, task.start, task.end)
        article = getattr(love_article, product.builder)(data, BRAND, narrate(product.key, data=data))
        cover = generate_sign_cover(task.sign, HEADLINES[product.key], period_text,
                                    OUTPUT_DIR / "images" / f"{stem}.png")
    else:
        rows = all_signs_data(task.start, task.end)
        narr = narrate("summary", rows=rows, start=task.start, end=task.end)
        article = love_article.build_summary(rows, task.start, task.end, BRAND, narr)
        cover = generate_ranking_cover("12星座の恋愛運ランキング", period_text, OUTPUT_DIR / "images" / f"{stem}.png")
    assert_clean(article.title, article.teaser, article.paid)
    md_path = OUTPUT_DIR / "articles" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(article.to_markdown(), encoding="utf-8")
    return article, cover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="予定と残り枠を表示するだけ")
    ap.add_argument("--now", help="現在時刻を指定（例: 2026-11-17T14:00）。動作確認用")
    args = ap.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else now_jst().replace(tzinfo=None)
    records = {key: load_record(key) for key in PRODUCTS}
    pending = [t for t in due_tasks(now)
               if not already_posted(records[t.product], t.product, t.start, t.sign_en)]

    day_used = recent_publish_count(24 * 60)
    hour_used = recent_publish_count(60)
    chosen = plan(pending, day_used, hour_used)

    logger.info(f"=== {now:%m/%d %H:%M} 未投稿 {len(pending)}本／直近24時間 {day_used}本（上限{MAX_PUBLISH_PER_DAY}）"
                f"／直近1時間 {hour_used}本（上限{MAX_PUBLISH_PER_HOUR}） → 今回 {len(chosen)}本 ===")
    for task in chosen:
        logger.info(f"  予定: {task.label()}")

    if args.dry_run:
        return

    from src.publishers.note_publisher import NotePublisher

    posted = 0
    for index, task in enumerate(chosen):
        product = PRODUCTS[task.product]
        article, cover = make_article(task)
        try:
            url = NotePublisher().publish_article(
                title=article.title, teaser_content=article.teaser, paid_content=article.paid,
                price=product.price, cover_image_path=cover, hashtags=article.hashtags,
            )
        except Exception as e:
            # 1本失敗すると後続も失敗しやすい（連続公開の制限）。残りは次の実行に回す
            logger.error(f"投稿失敗（{task.label()}）: {str(e).splitlines()[0][:160]}")
            logger.error("連続公開の制限にかかった可能性があるため、この回は打ち切ります（残りは次の実行で出します）")
            sys.exit(1)
        records[task.product].append({
            "product": task.product, "period_start": task.start.isoformat(), "sign": task.sign_en,
            "price": product.price, "url": url, "posted_at": now_jst().isoformat(timespec="seconds"),
        })
        save_record(task.product, records[task.product])
        posted += 1
        logger.info(f"[{index + 1}/{len(chosen)}] 投稿完了: {task.label()} {url}")
        if index < len(chosen) - 1:
            time.sleep(POST_INTERVAL)
    logger.info(f"=== 完了: {posted}本を投稿 ===")


if __name__ == "__main__":
    main()
