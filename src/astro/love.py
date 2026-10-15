"""星座ごとの恋愛運データ（期間の日別スコア・吉日・相性・ラッキーアイテム）

数値はすべて決定的に計算する。同じ星座・同じ期間なら、何度実行しても同じ結果になる。
暦（六曜・九星・干支・吉日）と月相を、星座のエレメントと重ねて点数にしている。
"""

import random
import zlib
from datetime import timedelta

from src.astro.moon import moon_events, phase_name
from src.astro.signs import ELEMENT_TO_GOGYO, ZODIAC_SIGNS, compat_comment, compat_score, sub_theme_for
from src.koyomi import SOJO, koyomi

SCORE_LABELS = {5: "絶好調", 4: "好調", 3: "穏やか", 2: "ひと休み", 1: "静かに過ごす"}
LUCKY_WORDS = [
    "ありがとう", "うれしい", "会いたい", "大丈夫", "そばにいて", "楽しかった",
    "助かった", "すてきだね", "また明日", "おつかれさま", "好きだよ", "ゆっくりしよう",
]
ACTIONS = {
    "火": ["こちらから連絡してみる", "思い切って誘ってみる", "新しい場所へ出かける"],
    "地": ["小さな贈り物を用意する", "手料理や手作りのものを渡す", "いつもの場所でゆっくり話す"],
    "風": ["長めのメッセージを送る", "気になっていた話題を振ってみる", "共通の友人に会う"],
    "水": ["相手の話をただ聴く", "写真や思い出を一緒に見る", "静かな場所で二人で過ごす"],
}


def _rng(sign: dict, start) -> random.Random:
    return random.Random(zlib.crc32(f"{sign['en']}-{start.isoformat()}".encode()))


def _affinity(sign_gogyo: str, day_gogyo: str) -> int:
    """星座のエレメント（五行に変換）と、その日の五行の相性"""
    if sign_gogyo == day_gogyo:
        return 1
    if SOJO.get(day_gogyo) == sign_gogyo:
        return 1
    if SOJO.get(sign_gogyo) == day_gogyo:
        return 0
    return -1


def day_score(sign: dict, day, ko: dict) -> tuple:
    """その日の恋愛運スコア（1〜5）と、理由になった要素"""
    reasons = []
    score = 2  # 平均が3前後になるよう、加点要素の多さに合わせて低めから始める
    gogyo = ELEMENT_TO_GOGYO[sign["element"]]
    affinity = _affinity(gogyo, ko["day_gogyo"])
    if affinity > 0:
        score += 1
        reasons.append(f"日の五行「{ko['day_gogyo']}」が{sign['element']}の星座と響き合う")
    elif affinity < 0:
        score -= 1
        reasons.append(f"日の五行「{ko['day_gogyo']}」とは少しぶつかる")

    if ko["rokuyo"] == "大安":
        score += 1
        reasons.append("六曜は大安")
    elif ko["rokuyo"] == "仏滅":
        score -= 1
        reasons.append("六曜は仏滅（仕切り直しの日）")

    if ko["lucky_days"]:
        score += 1
        reasons.append("・".join(ko["lucky_days"]) + "が重なる")

    phase = phase_name(day)
    if phase in ("新月", "満月"):
        score += 1
        reasons.append(f"{phase}の日")

    jitter = _rng(sign, day).randint(0, 1)
    score += jitter
    return max(1, min(5, score)), reasons


def period_data(sign: dict, start, end) -> dict:
    """期間中の恋愛運データ一式"""
    rng = _rng(sign, start)
    days = []
    cursor = start
    while cursor <= end:
        ko = koyomi(cursor)
        score, reasons = day_score(sign, cursor, ko)
        days.append({"date": cursor, "ko": ko, "score": score, "label": SCORE_LABELS[score],
                     "reasons": reasons, "phase": phase_name(cursor)})
        cursor += timedelta(days=1)

    ranked = sorted(days, key=lambda d: (-d["score"], d["date"]))
    others = [s for s in ZODIAC_SIGNS if s["en"] != sign["en"]]
    compat = sorted(others, key=lambda s: (-compat_score(sign, s), s["en"]))[:3]

    return {
        "sign": sign,
        "start": start,
        "end": end,
        "days": days,
        "best_days": ranked[:2],
        "caution_day": ranked[-1],
        "average": sum(d["score"] for d in days) / len(days),
        "compat": [{"sign": s, "score": compat_score(sign, s), "comment": compat_comment(sign, s)} for s in compat],
        "moon_events": moon_events(start, end),
        "sub_theme": sub_theme_for(start),
        "keywords": rng.sample(sign["love_keywords"], k=min(2, len(sign["love_keywords"]))),
        "lucky_word": rng.choice(LUCKY_WORDS),
        "action": rng.choice(ACTIONS[sign["element"]]),
        "color": sign["color"],
        "item": sign["item"],
        "place": sign["place"],
    }


def all_signs_data(start, end) -> list:
    """全星座分をスコアの高い順に（まとめ記事のランキング用）"""
    rows = [period_data(sign, start, end) for sign in ZODIAC_SIGNS]
    return sorted(rows, key=lambda r: (-r["average"], r["sign"]["en"]))
