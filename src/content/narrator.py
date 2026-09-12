"""物語的な文章パーツ（導入・回顧・反映・暦の読み解き・おわりに）の生成

数字や成績は計算済みの事実データから渡し、Gemini には言葉だけを書かせる。
APIキーが無い／失敗／NG表現が混ざった場合は、commentary のテンプレート文を使う。
"""

import json

from src.config import FEATURE_LABELS, FEATURES, Series
from src.content import commentary
from src.content.compliance import find_ng
from src.content.gemini_client import GeminiClient
from src.utils.dates import to_date, ymd_ja
from src.utils.logger import get_logger

logger = get_logger("narrator")

KEYS = ("hook", "review", "reflection", "koyomi", "message")
MIN_LEN, MAX_LEN = 150, 900

PROMPT = """あなたは「統計×暦」で宝くじの数字選びを研究する、人気の note ライターです。
データの話ばかりで殺伐としないよう、季節感や暦の由来、読者への語りかけを交えて、
思わず読み進めたくなる温かみのある文章パーツを日本語で書いてください。

# 厳守すること
- 事実データに無い数字・実績・確率は作らない。当せん番号や予想数字は書かない（事実データにある回号・当せん番号・重みの%は使ってよい）。
- 「必ず」「絶対」「確実」「当たる」「保証」「儲かる」「稼げる」「激熱」など、断定や射幸心をあおる表現は使わない。
- 抽せんは毎回無作為であり、分析や暦は「数字選びを楽しむための視点」という立場で書く。
- です・ます調。知的だけれど親しみやすいトーン。占いの言葉は「〜とされる」「〜と言われる」と上品に使う。絵文字は使わない。
- 段落の区切りには空行（\\n\\n）を入れる。
- backtest が true の場合、先週分は記事公開前のデータで再計算した検証であることに触れる。

# 出力形式（JSONのみ）
{{
  "hook": "記事冒頭の導入。350〜500字。季節感と抽せん日の暦の雰囲気→数字選びの楽しさへの共感→このノートの考え方（データと暦の二つの物差し、毎週の振り返り）の順に、読者を引き込む",
  "review": "先週の回顧コメント。250〜400字。惜しかった回や上振れ・下振れした分析軸を、事実どおりに物語として振り返る",
  "reflection": "今週の予想への反映の説明。250〜400字。重みを上げた軸・下げた軸（%の変化）と理由を、たとえ話を交えてわかりやすく。急な変更をしない方針にも触れる",
  "koyomi": "有料部分の暦の読み解き。400〜600字。六曜・九星・干支・暦注の吉日・五行の関係の由来や意味を紹介し、今回の数字選びの心構えにつなげる",
  "message": "記事の締めくくり。200〜350字。暦からのひとこと、無理のない範囲で楽しむ大切さ、次回の振り返りへの期待"
}}

# 事実データ
{facts}
"""


def build_facts(ctxs: list) -> dict:
    c = ctxs[0]
    ko = c["ko"]
    games = []
    for x in ctxs:
        wk = x["weekly"]
        games.append({
            "name": x["game"].name,
            "draw": x["draw"],
            "total_draws_analyzed": x["analysis"]["total"],
            "carryover_yen": x["last"].get("carryover", 0),
            "backtest": any(rv["backtest"] for rv in x["review_prev"]),
            "last_week": [
                {"draw": rv["draw"], "date": rv["date"],
                 "result": rv["result"].get("number") or rv["result"].get("main"),
                 "best_prize": rv["best"].get("prize") or "なし",
                 "best_match": rv["best"].get("matches", rv["best"].get("positions"))}
                for rv in x["review_prev"]
            ],
            "axis_results": [
                {"axis": FEATURE_LABELS[f], "hits": wk["totals"][f]["hits"], "expected": wk["totals"][f]["baseline"]}
                for f in FEATURES
            ] if wk["draws"] else [],
            "weights": [
                {"axis": FEATURE_LABELS[f], "before_pct": round(wk["before"][f] * 100, 1),
                 "after_pct": round(wk["after"][f] * 100, 1)}
                for f in FEATURES
            ],
        })
    return {
        "draw_date": ymd_ja(c["date"]),
        "season": commentary.SEASON[to_date(c["date"]).month],
        "koyomi": {k: ko[k] for k in ("rokuyo", "kyusei_name", "kanshi", "setsu_month_name", "lucky_days",
                                      "day_gogyo", "kyusei_gogyo", "relation", "relation_text", "numerology",
                                      "lucky_digits")},
        "koyomi_notes": {
            "rokuyo": commentary.ROKUYO_DETAIL[ko["rokuyo"]],
            "kyusei": commentary.KYUSEI_DETAIL[ko["kyusei"]],
            "lucky_days": {d: commentary.LUCKY_DETAIL[d] for d in ko["lucky_days"]},
        },
        "games": games,
    }


def fallback(series: Series, ctxs: list) -> dict:
    return {
        "hook": commentary.hook(series.key, ctxs),
        "review": commentary.review_story(series.key, ctxs),
        "reflection": commentary.reflection_story(series.key, ctxs),
        "koyomi": commentary.koyomi_reading(ctxs[0]["ko"]),
        "message": commentary.closing_message(series.key, ctxs),
    }


def narrate(series: Series, ctxs: list) -> dict:
    base = fallback(series, ctxs)
    try:
        client = GeminiClient()
    except ValueError as e:
        logger.info(f"テンプレート文を使用します（{e}）")
        return base

    facts = json.dumps(build_facts(ctxs), ensure_ascii=False, indent=1)
    try:
        generated = client.generate_json(PROMPT.format(facts=facts))
    except Exception as e:
        logger.warning(f"文章生成に失敗したためテンプレート文を使用します: {e}")
        return base

    out = dict(base)
    for key in KEYS:
        text = generated.get(key) if isinstance(generated, dict) else None
        if not isinstance(text, str) or not MIN_LEN <= len(text) <= MAX_LEN:
            logger.warning(f"文章パーツ {key} の形式・長さが不正なためテンプレート文を使用します")
            continue
        if find_ng(text):
            logger.warning(f"文章パーツ {key} にNG表現 {find_ng(text)} があるためテンプレート文を使用します")
            continue
        out[key] = text.strip()
    return out
