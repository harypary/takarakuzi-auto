from datetime import date, timedelta

from src.content import commentary
from src.content.compliance import find_ng
from src.koyomi import koyomi


def test_koyomi_texts_cover_all_days_without_ng():
    d = date(2026, 1, 1)
    seen_rokuyo, seen_lucky = set(), set()
    for _ in range(400):
        ko = koyomi(d)
        seen_rokuyo.add(ko["rokuyo"])
        seen_lucky.update(ko["lucky_days"])
        for text in (commentary.koyomi_reading(ko), commentary.koyomi_teaser(ko)):
            assert find_ng(text) == []
            assert "。。" not in text
        d += timedelta(days=1)
    assert seen_rokuyo == set(commentary.ROKUYO_DETAIL)
    assert seen_lucky <= set(commentary.LUCKY_DETAIL)


def test_phrase_pools_have_no_ng():
    pools = [commentary.HOOK_OPENERS, commentary.REVIEW_CLOSERS, commentary.REFLECT_OPENERS,
             commentary.CLOSERS, list(commentary.TIER_INTRO.values()), list(commentary.LUCKY_DETAIL.values()),
             list(commentary.FEATURE_STORY.values()), list(commentary.FEATURE_STORY_NEG.values())]
    for pool in pools:
        for text in pool:
            assert find_ng(text) == []
