from datetime import date

from src.content.column import TOPICS, choose_topic


def test_rotates_through_topics():
    today = date(2026, 10, 4)
    history = []
    picked = []
    for week in range(len(TOPICS)):
        topic = choose_topic(today, history)
        picked.append(topic)
        history.append({"topic": topic, "posted_at": today.isoformat()})
        today = date.fromordinal(today.toordinal() + 7)
    assert sorted(picked) == sorted(TOPICS)  # 4週で一巡し、重複しない


def test_reuses_oldest_after_a_full_cycle():
    history = [{"topic": t, "posted_at": f"2026-09-{6 + i * 7:02d}"} for i, t in enumerate(TOPICS)]
    # 一巡後は、いちばん古い種類に戻る
    assert choose_topic(date(2026, 10, 25), history) == TOPICS[0]
