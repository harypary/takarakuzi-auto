from datetime import date, timedelta

from src.astro.love import all_signs_data, period_data
from src.astro.moon import full_moons_between, moon_events, new_moons_between, phase_name
from src.astro.signs import BY_EN, COMPLEMENT, ZODIAC_SIGNS, compat_score, sub_theme_for


def test_twelve_signs_with_required_fields():
    assert len(ZODIAC_SIGNS) == 12
    for sign in ZODIAC_SIGNS:
        for key in ("name", "en", "symbol", "element", "modality", "love_style", "love_keywords", "color"):
            assert sign[key], f"{sign['en']} の {key} が空です"
        assert sign["element"] in ("火", "地", "風", "水")
        # 全角以外の文字が紛れていないか（文字化け対策）
        for word in sign["love_keywords"]:
            assert word.isprintable() and all(ord(c) > 127 for c in word.replace(" ", "")), word


def test_new_and_full_moons_2026_10():
    assert new_moons_between(date(2026, 10, 1), date(2026, 10, 31)) == [date(2026, 10, 11)]
    assert full_moons_between(date(2026, 10, 1), date(2026, 10, 31)) == [date(2026, 10, 26)]


def test_phase_name_matches_actual_events():
    assert phase_name(date(2026, 10, 11)) == "新月"
    assert phase_name(date(2026, 10, 26)) == "満月"
    # 満月は期間内で1日だけ
    names = [phase_name(date(2026, 10, 20) + timedelta(days=i)) for i in range(10)]
    assert names.count("満月") == 1


def test_period_data_is_deterministic_and_bounded():
    start, end = date(2026, 10, 19), date(2026, 10, 25)
    first = period_data(BY_EN["taurus"], start, end)
    second = period_data(BY_EN["taurus"], start, end)
    assert [d["score"] for d in first["days"]] == [d["score"] for d in second["days"]]
    assert first["action"] == second["action"]
    assert len(first["days"]) == 7
    assert all(1 <= d["score"] <= 5 for d in first["days"])
    assert len(first["compat"]) == 3
    assert first["sub_theme"]["label"]


def test_scores_are_not_all_maximum():
    rows = all_signs_data(date(2026, 10, 19), date(2026, 10, 25))
    averages = [r["average"] for r in rows]
    assert max(averages) <= 5 and min(averages) >= 1
    assert max(averages) - min(averages) > 0.2  # 星座ごとに差が出ている
    assert sum(averages) / len(averages) < 4.6  # 全員が満点ではない


def test_compat_prefers_same_or_complementary_element():
    taurus = BY_EN["taurus"]
    best = max((s for s in ZODIAC_SIGNS if s["en"] != "taurus"), key=lambda s: compat_score(taurus, s))
    assert best["element"] in (taurus["element"], COMPLEMENT[taurus["element"]])


def test_sub_theme_rotates_by_week():
    labels = {sub_theme_for(date(2026, 10, 5) + timedelta(days=7 * i))["label"] for i in range(5)}
    assert len(labels) == 5  # 5週で5種類
