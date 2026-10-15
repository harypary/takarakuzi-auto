import re
from datetime import date

import pytest

from src.astro.love import all_signs_data, period_data
from src.astro.signs import ZODIAC_SIGNS
from src.content import love_article
from src.content.compliance import find_ng
from src.content.love_narrator import narrate

START, END = date(2026, 10, 19), date(2026, 10, 25)
# 12.uranai の実測（300円で有料5,250字、1,980円で9,000字）に合わせた下限
MIN_PAID = {"daily": 4500, "summary": 4500, "weekly": 6500, "intensive": 9000}
# 日本語・英数字・記号以外（キリル文字やハングルなど）が紛れていないか
FOREIGN = re.compile(r"[Ѐ-ӿ가-힯؀-ۿ]")


def _article(product: str, sign_en: str = "libra"):
    sign = next(s for s in ZODIAC_SIGNS if s["en"] == sign_en)
    if product == "summary":
        rows = all_signs_data(START, START)
        return love_article.build_summary(rows, START, START, "恋の星読み",
                                          narrate("summary", rows=rows, start=START, end=START))
    end = {"daily": START, "weekly": END}.get(product, date(2026, 11, 1))
    data = period_data(sign, START, end)
    builder = {"daily": love_article.build_daily, "weekly": love_article.build_weekly,
               "intensive": love_article.build_intensive}[product]
    return builder(data, "恋の星読み", narrate(product, data=data))


@pytest.mark.parametrize("product", ["daily", "summary", "weekly", "intensive"])
def test_paid_length_matches_price(product):
    article = _article(product)
    assert len(article.paid) >= MIN_PAID[product], f"{product}: 有料部分が短い（{len(article.paid)}字）"
    assert 300 <= len(article.teaser) <= 1200


@pytest.mark.parametrize("product", ["daily", "summary", "weekly", "intensive"])
def test_no_foreign_characters_or_ng_words(product):
    article = _article(product)
    whole = f"{article.title}\n{article.teaser}\n{article.paid}"
    found = FOREIGN.findall(whole)
    assert not found, f"{product}: 異国の文字が混入 {set(found)}"
    assert find_ng(whole) == [], f"{product}: NG表現 {find_ng(whole)}"


def test_every_sign_builds_without_error():
    for sign in ZODIAC_SIGNS:
        data = period_data(sign, START, END)
        article = love_article.build_weekly(data, "恋の星読み", narrate("weekly", data=data))
        assert sign["name"] in article.title
        assert not FOREIGN.search(article.paid), sign["name"]
        assert len(article.paid) >= MIN_PAID["weekly"]
