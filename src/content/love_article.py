"""恋愛占い記事の組み立て（3商品）

  weekly     980円  星座別・週間恋愛運（毎週月曜・12本）
  intensive 1980円  星座別・2週間の恋愛集中鑑定（隔週木曜・12本）
  summary    500円  全星座まとめ（火・金・各1本）

恋愛を主軸にしつつ、回ごとに「暮らしのテーマ」（仕事・人づきあい・お金・心と体・家族）を1つ添える。
数値・日付・相性はすべて src.astro の計算結果、長い文章は src.content.love_narrator が用意する。
"""

from dataclasses import dataclass

from src.astro.signs import ZODIAC_SIGNS, compat_comment, compat_score
from src.content.love_deep import (SIGN_DEEP, arc_section, bad_phrase_section, choice_section,
                                   evening_review, key_day_section, partner_shift_section,
                                   pitfall_section, question_section, theme_section, words_section)
from src.content.love_sections import (MOON_ADVICE, ROKUYO_TIME, day_details, element_advice,
                                       moon_rituals, roadmap)
from src.utils.dates import md_wd, ymd_ja

SEP = "━━━━━━━━━━━━━━━━━━"
STARS = {5: "★★★★★", 4: "★★★★☆", 3: "★★★☆☆", 2: "★★☆☆☆", 1: "★☆☆☆☆"}

DISCLAIMER = (
    "【ご注意】\n"
    "この記事は、西洋占星術と暦（六曜・九星・干支・月の満ち欠け）をもとにした読みものです。"
    "書かれている内容は未来を約束するものではありません。最後に決めるのはいつもあなた自身です。"
    "気になる日や言葉を、毎日の背中を押すきっかけとして使っていただけたらうれしいです。"
)


@dataclass
class Article:
    title: str
    teaser: str
    paid: str
    hashtags: list

    def to_markdown(self) -> str:
        return (f"# {self.title}\n\n{self.teaser}\n\n=============== ここから有料 ===============\n\n"
                f"{self.paid}\n\nハッシュタグ: {' '.join('#' + t for t in self.hashtags)}\n")


def _h(title: str) -> str:
    return f"{SEP}\n■ {title}\n{SEP}"


def _range_text(start, end) -> str:
    wd = "月火水木金土日"
    return f"{start.month}/{start.day}（{wd[start.weekday()]}）〜{end.month}/{end.day}（{wd[end.weekday()]}）"


def _day_lines(data: dict) -> list:
    lines = []
    for day in data["days"]:
        ko = day["ko"]
        extra = []
        if day["phase"] in ("新月", "満月"):
            extra.append(day["phase"])
        if ko["lucky_days"]:
            extra.append("・".join(ko["lucky_days"]))
        tail = f"　【{'／'.join(extra)}】" if extra else ""
        lines.append(f"{md_wd(day['date'])}　{STARS[day['score']]}　{day['label']}　（{ko['rokuyo']}／{ko['kyusei_name']}）{tail}")
    return lines


def _moon_lines(data: dict) -> list:
    if not data["moon_events"]:
        return ["この期間に新月・満月はありません。月は少しずつ形を変えながら、静かに見守ってくれています。"]
    lines = []
    for event in data["moon_events"]:
        lines.append(f"・{ymd_ja(event['date'])}　{event['kind']}　{event['meaning']}")
        if event["kind"] == "新月":
            lines.append("　新しい関係を始めたい方は、この日に「どんな関係を築きたいか」を言葉にしてみてください。")
        else:
            lines.append("　満ちた月は、手放しの合図でもあります。迷っている関係があるなら、気持ちの整理に向く日です。")
    return lines


def _lucky_lines(data: dict) -> list:
    return [
        f"・いちばんの行動：{data['action']}",
        f"・口にすると流れが変わる言葉：「{data['lucky_word']}」",
        f"・ラッキーカラー：{data['color']}",
        f"・心が整うもの：{data['item']}",
        f"・縁がつながりやすい場所：{data['place']}",
    ]


def _hashtags(sign: dict) -> list:
    return [sign["name"], "恋愛", "恋愛運", "占い", "星座占い", "恋愛占い", "12星座", "運勢", "開運", "恋"]


# ───────────────────────── 300円・毎日 ─────────────────────────

def build_daily(data: dict, brand: str, narr: dict) -> Article:
    sign, theme = data["sign"], data["sub_theme"]
    deep = SIGN_DEEP[sign["en"]]
    day = data["days"][0]
    ko = day["ko"]
    date_text = ymd_ja(day["date"])
    title = f"【{sign['name']}】{md_wd(day['date'])}の恋愛運｜「{data['keywords'][0]}」の日【{brand}】"

    teaser = "\n".join([
        f"{sign['name']}のあなたへ。{deep['core'].split('。')[0]}。",
        "",
        f"{date_text}の恋愛運は{STARS[day['score']]}（{day['label']}）。"
        f"六曜は{ko['rokuyo']}、日の九星は{ko['kyusei_name']}、月は{day['phase']}です。"
        + (f"さらに{'・'.join(ko['lucky_days'])}が重なります。" if ko["lucky_days"] else ""),
        "",
        f"今日のテーマは「{data['keywords'][0]}」。{ROKUYO_TIME[ko['rokuyo']]}。",
        "",
        _h("この先で読めること"),
        "・今日あなたに流れているもの（暦から読む、今日の意味）",
        "・朝・昼・夜、それぞれの過ごし方",
        "・相手の気持ちと、反応の読み方",
        f"・{sign['name']}が今日つまずきやすいところ",
        "・相手に届く言葉（文例と、なぜ効くのか）",
        "・片思い／交際中／復縁、それぞれの動き方",
        "・今日の行動プランと、ひとつの問い",
        "",
        DISCLAIMER,
    ])

    paid = [_h(f"{date_text}、{sign['name']}に流れているもの"), deep["core"], "",
            f"その{sign['name']}にとって、今日は「{data['keywords'][0]}」が主題になる一日です。",
            f"恋愛運は{STARS[day['score']]}。"
            + ("追い風です。動くなら今日がその日です。" if day["score"] >= 4 else
               "凪の日です。無理に動かず、整えるほうが得るものがあります。" if day["score"] == 3 else
               "向かい風です。今日は自分を労わる日にあててください。"),
            "",
            f"理由は暦にあります。{'／'.join(day['reasons']) if day['reasons'] else '日の巡りが穏やかに整っています'}。"
            f"日の干支は{ko['kanshi']}、五行は{ko['day_gogyo']}。"
            f"{sign['element']}のエレメントを持つ{sign['name']}との関係で、今日の流れが決まります。",
            "", deep["desire"],
            "それを思い出しておくと、今日のやりとりに振り回されにくくなります。",
            "", _h("今日の暦を読む"),
            f"・六曜：{ko['rokuyo']}　{ROKUYO_TIME[ko['rokuyo']]}",
            f"・九星（日盤）：{ko['kyusei_name']}",
            f"・干支：{ko['kanshi']}（五行は{ko['day_gogyo']}）",
            f"・月：{day['phase']}　{MOON_ADVICE.get(day['phase'], '')}",
            f"・暦注の吉日：{'・'.join(ko['lucky_days']) if ko['lucky_days'] else 'なし'}",
            "",
            "暦は、その日の空気の質を教えてくれます。良し悪しではなく、"
            "「押すのに向く日か、待つのに向く日か」を知るための目安だと考えてください。",
            "", _h("朝・昼・夜の過ごし方")] + key_day_section(data) + [
        "", _h("相手の気持ちと、反応の読み方"),
        f"今日のあなたは、{deep['words'].split('。')[0]}。その前提で相手を見てみてください。",
        "",
        "■ 相手の反応をどう読むか",
        "　・返事が短い　→　気持ちの問題ではなく、状況の問題であることが多いです",
        "　・返事が遅い　→　考えてから返したい相手ほど遅くなります。雑に扱われているわけではありません",
        "　・質問が返ってくる　→　会話を続けたい意思表示です。素直に答えてください",
        "　・予定を聞かれる　→　もっとも分かりやすい好意のサインです",
        "",
        f"{sign['name']}のあなたは、{deep['pitfall'].split('。')[0]}という癖があります。"
        "今日その癖が出そうになったら、一度深呼吸して、相手の立場を想像してみてください。",
        "", _h(f"{sign['name']}が今日つまずきやすいところ"),
        deep["pitfall"], "",
        "■ 抜け方", f"　{deep['escape']}", "",
        "■ 無理をしているサイン", f"　{deep['strain']}",
        "　当てはまったら、今日は恋愛から少し離れて、自分の生活を整えるほうを優先してください。",
        "", _h("相手に届く言葉")] + words_section(data) + [
        "", _h("今日あなたと響き合う星座")]
    for rank, row in enumerate(data["compat"], 1):
        paid += [f"■ {rank}位　{row['sign']['name']}（相性 {STARS[row['score']]}）", f"　{row['comment']}"]
    paid += ["", narr["compat_note"],
             "", _h("動く・待つ・整える、どれを選ぶか")] + choice_section(data) + [
        "", _h("つい言ってしまう一言")] + bad_phrase_section(data) + [
        "", _h("立場別の動き方"), narr["scenes"],
        "", _h(f"今日のもうひとつのテーマ：{theme['label']}"), narr["sub_theme"],
        "", _h("今日の行動プラン")] + _lucky_lines(data) + [
        "", _h("夜の振り返り")] + evening_review(data) + [
        "", _h("今日の問い")] + question_section(data) + [
        "", _h("今日のあなたへ"), narr["closing"], "", DISCLAIMER]
    return Article(title, teaser, "\n".join(paid), _hashtags(sign))


# ───────────────────────── 980円・週間 ─────────────────────────

def build_weekly(data: dict, brand: str, narr: dict) -> Article:
    sign, theme = data["sign"], data["sub_theme"]
    period = _range_text(data["start"], data["end"])
    title = f"【{sign['name']}の週間恋愛運】{period}｜「{data['keywords'][0]}」が動く一週間【{brand}】"

    teaser = "\n".join([
        narr["intro"],
        "",
        _h(f"今週（{period}）の全体像"),
        f"・週全体の恋愛運：{STARS[round(data['average'])]}（7日間の平均）",
        f"・今週のキーワード：{'、'.join(data['keywords'])}",
        f"・暮らしのテーマ：{theme['label']}",
        f"・{sign['name']}の恋のかたち：{sign['love_style']}",
        "",
        _h("この先で読めること"),
        f"・今週の{sign['name']}に流れているもの（なぜこの一週間がこう動くのか）",
        "・今週を三幕で追う（いつ様子を見て、いつ動くか）",
        "・いちばん動きやすい日の、朝・昼・夜の過ごし方",
        f"・{sign['name']}がつまずきやすいところと、その抜け方",
        "・相手に届く言葉（そのまま使える文例と、なぜ効くのかの説明）",
        "・片思い／交際中／復縁、それぞれの動き方",
        "・新月・満月の使い方（願いごと・手放しの文例つき）",
        f"・{theme['label']}へのアドバイス",
        "・今週の行動プランと、最後にひとつの問い",
        "",
        DISCLAIMER,
    ])

    best = data["best_days"]
    caution = data["caution_day"]
    paid = [_h(f"今週の{sign['name']}に流れているもの")] + theme_section(data) + [
        "", _h("7日間の流れ（一覧）")] + _day_lines(data) + [
        "",
        f"星の数は、その日の暦（六曜・五行・暦注の吉日）と月の満ち欠けを、{sign['element']}のエレメントと重ねて出しています。",
        "",
        narr["flow"],
        "", _h("今週を三幕で追う")] + arc_section(data) + [
        _h(f"いちばん動きやすい日：{md_wd(best[0]['date'])}")] + key_day_section(data) + [
        "", _h("1日ずつの読み解き")] + day_details(data) + [
        _h("相手の気持ちは、どう動きそうか")] + partner_shift_section(data) + [
        "", _h(f"{sign['name']}がつまずきやすいところ")] + pitfall_section(data) + [
        "", _h("相手に届く言葉")] + words_section(data) + [
        "", _h("今週あなたと響き合う星座")]
    for rank, row in enumerate(data["compat"], 1):
        paid += [f"■ {rank}位　{row['sign']['name']}（相性 {STARS[row['score']]}）", f"　{row['comment']}"]
    paid += ["", narr["compat_note"],
             "", _h("立場別の動き方"), narr["scenes"],
             "", _h("新月・満月の使い方")] + moon_rituals(data) + [
        _h(f"今週のもうひとつのテーマ：{theme['label']}"), narr["sub_theme"],
        "", _h("今週の行動プラン")] + _lucky_lines(data) + [
        f"・動く日：{md_wd(best[0]['date'])}、{md_wd(best[1]['date'])}",
        f"・整える日：{md_wd(caution['date'])}",
        "", _h("今週の問い")] + question_section(data) + [
        "", _h("今週のあなたへ"), narr["closing"], "", DISCLAIMER]
    return Article(title, teaser, "\n".join(paid), _hashtags(sign))


# ───────────────────────── 1,980円・2週間の集中鑑定 ─────────────────────────

def build_intensive(data: dict, brand: str, narr: dict) -> Article:
    sign, theme = data["sign"], data["sub_theme"]
    period = _range_text(data["start"], data["end"])
    title = (f"【{sign['name']}・2週間の恋愛集中鑑定】{period}"
             f"｜片思い・交際中・復縁それぞれの動き方【{brand}】")

    first, second = data["days"][:7], data["days"][7:]
    avg_first = sum(d["score"] for d in first) / len(first)
    avg_second = sum(d["score"] for d in second) / max(len(second), 1)
    trend = ("後半にかけて追い風が強まります。" if avg_second > avg_first else
             "前半のうちに動いておきたい巡りです。" if avg_second < avg_first else "波の少ない、落ち着いた2週間です。")

    teaser = "\n".join([
        narr["intro"],
        "",
        _h(f"この2週間（{period}）の全体像"),
        f"・前半（{_range_text(first[0]['date'], first[-1]['date'])}）：{STARS[round(avg_first)]}",
        f"・後半（{_range_text(second[0]['date'], second[-1]['date'])}）：{STARS[round(avg_second)]}",
        f"・{trend}",
        f"・キーワード：{'、'.join(data['keywords'])}",
        f"・暮らしのテーマ：{theme['label']}",
        "",
        _h("この鑑定で読めること"),
        "・14日間すべての恋愛運（星の数・六曜・九星・月の満ち欠け）",
        "・恋が動く日ベスト3と、その日に起きやすいこと",
        "・片思い／交際中／復縁それぞれの、具体的な動き方",
        "・12星座すべてとの相性と、相手別の接し方",
        "・新月・満月の使い方（願いの書き方・手放し方）",
        f"・{theme['label']}への向き合い方",
        "・2週間の行動プランと、動く日・整える日",
        "",
        "週間の記事より踏み込んで、「いつ・誰に・どう動くか」までお伝えします。",
        "",
        DISCLAIMER,
    ])

    ranked = sorted(data["days"], key=lambda d: (-d["score"], d["date"]))[:3]
    scenes_hint = ["連絡が来る、または返事が早くなる", "思いがけず会える、予定が重なる", "相手の本音がこぼれる"]
    paid = [_h(f"{sign['name']}の2週間（14日間）の恋愛運")] + _day_lines(data) + [
        "",
        f"前半の平均は{avg_first:.1f}、後半は{avg_second:.1f}。{trend}",
        "",
        narr["flow"],
        "",
        _h("恋が動く日 ベスト3"),
    ]
    for rank, (day, hint) in enumerate(zip(ranked, scenes_hint), 1):
        paid += [f"■ {rank}位　{ymd_ja(day['date'])}　{STARS[day['score']]}（{day['ko']['rokuyo']}・{day['phase']}）",
                 f"　理由：{'／'.join(day['reasons']) if day['reasons'] else '暦が穏やかに整う日です'}",
                 f"　起きやすいこと：{hint}"]
    paid += ["", narr["best_days"],
             "", _h(f"この2週間の{sign['name']}に流れているもの")] + theme_section(data) + [
        "", _h("2週間を三幕で追う")] + arc_section(data) + [
        _h("2週間の見取り図")] + roadmap(data) + [
        "", _h(f"いちばん動きやすい日：{md_wd(ranked[0]['date'])}")] + key_day_section(data) + [
        "", _h("1日ずつの読み解き（14日間）")] + day_details(data) + [
        _h("相手の気持ちは、どう動きそうか")] + partner_shift_section(data) + [
        "", _h(f"{sign['name']}がつまずきやすいところ")] + pitfall_section(data) + [
        "", _h("相手に届く言葉")] + words_section(data) + [
        "", _h("立場別の動き方"), narr["scenes"],
        "", _h("12星座すべてとの相性")]
    for other in sorted(ZODIAC_SIGNS, key=lambda s: (-compat_score(sign, s), s["en"])):
        if other["en"] == sign["en"]:
            continue
        paid.append(f"・{other['name']}（{STARS[compat_score(sign, other)]}）{compat_comment(sign, other)}")
    paid += ["", narr["compat_note"],
             "", _h("新月・満月の使い方")] + moon_rituals(data) + [
        _h(f"もうひとつのテーマ：{theme['label']}"), narr["sub_theme"],
        "", _h("2週間の問い")] + question_section(data) + [
        "", _h("2週間の行動プラン")] + _lucky_lines(data) + [
        f"・動く日：{md_wd(ranked[0]['date'])}、{md_wd(ranked[1]['date'])}、{md_wd(ranked[2]['date'])}",
        f"・整える日：{md_wd(data['caution_day']['date'])}",
        "", _h("この2週間のあなたへ"), narr["closing"], "", DISCLAIMER]
    return Article(title, teaser, "\n".join(paid), _hashtags(sign))


# ───────────────────────── 500円・全星座まとめ ─────────────────────────

def build_summary(rows: list, start, end, brand: str, narr: dict) -> Article:
    theme = rows[0]["sub_theme"]
    period = _range_text(start, end)
    title = f"【12星座の恋愛運ランキング】{period}｜1位は{rows[0]['sign']['name']}【{brand}】"

    teaser = "\n".join([
        narr["intro"],
        "",
        _h("上位3星座"),
    ] + [
        f"{rank}位　{row['sign']['name']}　{STARS[round(row['average'])]}　キーワード：{row['keywords'][0]}"
        for rank, row in enumerate(rows[:3], 1)
    ] + [
        "",
        f"今回の暮らしのテーマは「{theme['label']}」。恋愛と並行して、{theme['lead']}が気になりやすい時期です。",
        "",
        _h("この先で読めること"),
        "・12星座すべての順位と恋愛運",
        "・星座ごとのキーワードと、ひとことアドバイス",
        "・星座ごとに恋が動きやすい日",
        "・この期間の暦と月の動き",
        "",
        DISCLAIMER,
    ])

    paid = [_h(f"12星座の恋愛運ランキング（{period}）")]
    for rank, row in enumerate(rows, 1):
        sign = row["sign"]
        best = row["best_days"][0]
        caution = row["caution_day"]
        paid += [
            f"{rank}位　{sign['name']}（{sign['period']}生まれ）　{STARS[round(row['average'])]}",
            f"　キーワード：{'、'.join(row['keywords'])}",
            f"　恋が動く日：{md_wd(best['date'])}（{best['ko']['rokuyo']}）"
            f"／気をつけたい日：{md_wd(caution['date'])}（{caution['ko']['rokuyo']}）",
            f"　この期間は、{row['action']}と流れに乗れます。{sign['love_style']}",
            f"　{sign['name']}の魅力は{'と'.join(sign['keywords'][:2])}。恋愛では「{sign['love_keywords'][0]}」として表れます。"
            "うまくいかない日があっても、それは相性の問題ではなく巡りの問題です。",
            f"　相性が良いのは{'、'.join(c['sign']['name'] for c in row['compat'])}。"
            f"　口にすると良い言葉：「{row['lucky_word']}」／ラッキーカラー：{row['color']}／"
            f"縁がつながる場所：{row['place']}",
            "",
        ]
    paid += [narr["flow"], "", _h("この期間の日別の暦")]
    for day in rows[0]["days"]:
        ko = day["ko"]
        lucky = f"／{'・'.join(ko['lucky_days'])}" if ko["lucky_days"] else ""
        paid.append(f"■ {md_wd(day['date'])}　{ko['rokuyo']}／{ko['kyusei_name']}／月は{day['phase']}{lucky}")
        paid.append(f"　{ROKUYO_TIME[ko['rokuyo']]}。")
    paid += ["", _h("上位3星座をもう少しくわしく")]
    for rank, row in enumerate(rows[:3], 1):
        sign = row["sign"]
        paid += [
            f"■ {rank}位　{sign['name']}　{STARS[round(row['average'])]}",
            f"　{sign['love_style']}",
            f"　この期間は「{'、'.join(row['keywords'])}」がテーマ。{row['action']}と流れに乗れます。",
            f"　相性が良いのは{'、'.join(c['sign']['name'] for c in row['compat'])}。",
            f"　口にすると良い言葉：「{row['lucky_word']}」／ラッキーカラー：{row['color']}",
            "",
        ]
    paid += [_h("エレメント別の過ごし方")] + element_advice() + [
        _h("この期間の暦と月")] + _moon_lines(rows[0]) + [
        "",
        _h(f"もうひとつのテーマ：{theme['label']}"),
        f"{theme['lead']}について、迷いが出やすい期間です。恋愛も{theme['advice_focus']}も、根っこは「自分がどうしたいか」。"
        "順位が低かった星座の方も、静かに整える時間と考えれば損ではありません。",
        "",
        narr["closing"],
        "",
        DISCLAIMER,
    ]
    return Article(title, teaser, "\n".join(paid),
                   ["恋愛運", "12星座", "星座占い", "恋愛占い", "ランキング", "占い", "運勢", "恋", "開運", "今週の運勢"])
