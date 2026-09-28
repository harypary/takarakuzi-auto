"""ジャンボ宝くじの無料記事（買う日を暦で選ぶ）の組み立て

ジャンボは番号が印刷済みで予想が成立しないため、「いつ買うか」を暦から考える読みもの。
吉日は src.koyomi の計算結果をそのまま使う。
"""

from dataclasses import dataclass
from datetime import date, timedelta

from src.config import MODEL_NAME, SERIES
from src.content.article import _h, _intro_link
from src.content.commentary import LUCKY_DETAIL, SEASON
from src.content.compliance import DISCLAIMER
from src.koyomi import koyomi
from src.utils.dates import md_wd, ymd_ja

HASHTAGS = ["宝くじ", "ジャンボ宝くじ", "ハロウィンジャンボ", "開運", "一粒万倍日",
            "天赦日", "占い", "暦", "金運", "数字選択式宝くじ"]

# 吉日の格付け（強い順）。記事内の「特におすすめの日」に使う
RANK = ["天赦日", "一粒万倍日", "己巳の日", "寅の日", "巳の日", "甲子の日"]

# 六曜ごとの「買いに行く時間帯」の目安（ジャンボ向けの言い回し）
BUY_ADVICE = {
    "大安": "時間帯を気にせず、落ち着いて買いに行ける日",
    "友引": "朝と夕方が吉とされる日。お昼前後は避けるのが暦らしい過ごし方",
    "先勝": "午前中が吉とされる日。早めに売り場へ向かうのがおすすめ",
    "先負": "午後が吉とされる日。急がず、ゆっくり出かけるのが似合います",
    "赤口": "正午前後だけが吉とされる日。お昼どきに立ち寄るのがおすすめ",
    "仏滅": "区切りや仕切り直しに向くとされる日。新しい気持ちで一枚買うのに合います",
}


@dataclass(frozen=True)
class Jumbo:
    name: str
    sale_start: date
    sale_end: date
    draw_date: date
    payout_start: date
    price: int
    first_prize: str
    first_with_adjacent: str
    second_prize: str
    odds: str
    mini_name: str
    mini_first: str
    mini_with_adjacent: str
    online: bool


def _lucky_score(ko: dict) -> int:
    score = sum(RANK.index(d) < 3 and 3 or 1 for d in ko["lucky_days"] if d in RANK)
    if ko["rokuyo"] == "大安":
        score += 1
    return score


def build_jumbo(jumbo: Jumbo, today: date) -> tuple:
    title = (
        f"【{jumbo.name}】買うならこの日｜暦でえらぶ{jumbo.sale_end.month}月の吉日カレンダー"
        f"（天赦日・一粒万倍日・大安）【{MODEL_NAME}】"
    )

    days = []
    day = max(today, jumbo.sale_start)
    while day <= jumbo.sale_end:
        ko = koyomi(day)
        days.append((day, ko, _lucky_score(ko)))
        day += timedelta(days=1)
    best = sorted(days, key=lambda x: (-x[2], x[0]))[:3]

    P = [
        f"{SEASON[today.month]}。{jumbo.name}の発売がはじまっています。",
        "",
        "ジャンボ宝くじは、ロトやナンバーズと違って番号があらかじめ印刷されています。"
        "つまり「どの数字を選ぶか」ではなく、「いつ、どんな気持ちで買うか」が、こちらで決められる唯一のことです。",
        "",
        "そこでこの記事では、発売期間に残っている日を暦で読み解き、昔から縁起がよいとされる日を一覧にしました。"
        "数字選択式の予想記事と同じく、暦は「迷ったときの決め手」として使うのがおすすめです。",
        "",
        _h(f"{jumbo.name}の基本情報"),
        f"・発売期間：{ymd_ja(jumbo.sale_start)} 〜 {ymd_ja(jumbo.sale_end)}",
        f"・抽せん日：{ymd_ja(jumbo.draw_date)}",
        f"・当せん金の支払開始：{ymd_ja(jumbo.payout_start)}",
        f"・1枚：{jumbo.price}円",
        f"・1等：{jumbo.first_prize}（前後賞と合わせて{jumbo.first_with_adjacent}）",
        f"・2等：{jumbo.second_prize}",
        f"・1等の当せん確率：{jumbo.odds}",
        f"・{jumbo.mini_name}：1等 {jumbo.mini_first}、前後賞と合わせて{jumbo.mini_with_adjacent}",
        "・宝くじ公式サイトでも購入できます。" if jumbo.online else "・売り場での購入のみです。",
        "",
        _h("暦でえらぶ「買うならこの日」ベスト3"),
    ]
    for rank, (day, ko, _) in enumerate(best, 1):
        lucky = "・".join(ko["lucky_days"]) or "特別な暦注はなし"
        P.append(f"■ {rank}位　{ymd_ja(day)}")
        P.append(f"　{lucky}／六曜は{ko['rokuyo']}／日の九星は{ko['kyusei_name']}")
        for d in ko["lucky_days"]:
            P.append(f"　{LUCKY_DETAIL[d]}")
        P.append(f"　{BUY_ADVICE[ko['rokuyo']]}です。")
        P.append("")

    P += [
        _h(f"発売期間の暦カレンダー（{md_wd(max(today, jumbo.sale_start))}〜{md_wd(jumbo.sale_end)}）"),
        "日付／六曜／九星／暦注の吉日",
    ]
    for day, ko, score in days:
        lucky = "・".join(ko["lucky_days"])
        mark = "★" if score >= 3 else ("○" if score >= 1 else "　")
        P.append(f"{mark} {md_wd(day)}　{ko['rokuyo']}／{ko['kyusei_name']}" + (f"／{lucky}" if lucky else ""))

    P += [
        "",
        "★＝天赦日や一粒万倍日などが重なる日、○＝大安や吉日がある日です。",
        "",
        _h("暦の吉日は、どんな日？"),
    ]
    for name in ("天赦日", "一粒万倍日", "寅の日", "巳の日"):
        P.append(f"■ {name}")
        P.append(f"　{LUCKY_DETAIL[name]}")
    P += [
        "",
        _h("買い方の考え方"),
        "・ジャンボは番号が印刷済みなので、どの番号を買っても当せん確率は同じです。連番でもバラでも変わりません。",
        "・連番は1等と前後賞を同時に狙える買い方、バラは当たる機会を広く取る買い方、という違いがあります。",
        "・当せん確率は宝くじの中でも低い部類です。無理のない金額で、抽せん日までの時間を楽しむのが健やかな付き合い方だと考えています。",
        "",
        _h("数字を選ぶ宝くじもあります"),
        "「自分で数字を選びたい」という方には、ロト6・ロト7・ナンバーズ3・4があります。"
        "このノートでは、過去の全データの統計と暦を組み合わせて、毎回の予想と検証を公開しています。",
    ]
    for key in ("numbers", "loto6", "loto7"):
        s = SERIES[key]
        P.append(f"・{s.title_name}予想（{s.price}円）")
    P += _intro_link()
    P += ["", DISCLAIMER]
    return title, "\n".join(P), list(HASHTAGS)
