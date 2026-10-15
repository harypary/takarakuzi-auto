"""恋愛占い記事の文章パーツ生成

日付・星の数・相性・暦はすべて計算済みの事実を渡し、Gemini には言葉だけを書かせる。
APIキーが無い／失敗／長さが足りない場合は、テンプレート文に差し替える（テンプレートも長めに書く）。
"""

import json
import random
import zlib

from src.content.gemini_client import GeminiClient
from src.utils.dates import md_wd, ymd_ja
from src.utils.logger import get_logger

logger = get_logger("love_narrator")

# 商品ごとに必要なパーツと、目標の文字数（下限, 上限）
SPECS = {
    "daily": {
        "intro": (220, 380), "flow": (260, 420), "best_days": (260, 420),
        "scenes": (550, 900), "compat_note": (220, 380), "sub_theme": (260, 420), "closing": (220, 380),
    },
    "weekly": {
        "intro": (260, 420), "flow": (320, 520), "best_days": (320, 520),
        "scenes": (650, 1000), "compat_note": (260, 420), "sub_theme": (320, 520), "closing": (260, 420),
    },
    "intensive": {
        "intro": (320, 520), "flow": (420, 650), "best_days": (420, 700),
        "scenes": (1100, 1700), "compat_note": (420, 650), "sub_theme": (420, 650), "closing": (320, 520),
    },
    "summary": {
        "intro": (260, 420), "flow": (320, 520), "closing": (220, 380),
    },
}

PROMPT = """あなたは、やさしい言葉で心に届く文章を書く恋愛占いのライターです。
下の事実データだけを使って、note の記事に入れる文章パーツを日本語で書いてください。

# 厳守すること
- 事実データにない日付・星の数・星座名・出来事を作らない。
- 「必ず」「絶対」「確実」など、未来を断定する言い方はしない。「〜しやすい」「〜かもしれません」と書く。
- 読者は一人の人。「あなた」と呼びかけ、やわらかい敬体（です・ます）で書く。絵文字は使わない。
- 不安をあおらない。うまくいかない日も、責めずに「そういう巡り」として書く。
- 占いは背中を押すための読みもので、決めるのは本人だという姿勢を保つ。
- 段落の区切りには空行（\\n\\n）を入れる。

# 出力形式（JSONのみ。各値は指定の文字数を守る）
{keys}

# 事実データ
{facts}
"""

ROKUYO_HINT = {
    "大安": "一日を通して流れが穏やかな日", "友引": "朝と夕方に動きやすい日",
    "先勝": "午前中に動くと良い日", "先負": "午後のほうが落ち着いて進む日",
    "赤口": "お昼どきだけ流れが整う日", "仏滅": "いったん区切りをつけるのに向く日",
}


def _rng(data: dict, salt: str = "") -> random.Random:
    return random.Random(zlib.crc32(f"{data['sign']['en']}-{data['start']}-{salt}".encode()))


def build_facts(product: str, data: dict) -> dict:
    sign = data["sign"]
    return {
        "product": product,
        "sign": {"name": sign["name"], "element": sign["element"], "ruling_planet": sign["ruling_planet"],
                 "keywords": sign["keywords"], "love_style": sign["love_style"],
                 "love_keywords": sign["love_keywords"]},
        "period": f"{ymd_ja(data['start'])}〜{ymd_ja(data['end'])}",
        "average_score": round(data["average"], 1),
        "days": [{"date": md_wd(d["date"]), "score": d["score"], "label": d["label"],
                  "rokuyo": d["ko"]["rokuyo"], "lucky_days": d["ko"]["lucky_days"], "moon": d["phase"]}
                 for d in data["days"]],
        "best_days": [{"date": ymd_ja(d["date"]), "score": d["score"], "reasons": d["reasons"]}
                      for d in data["best_days"]],
        "caution_day": {"date": ymd_ja(data["caution_day"]["date"]), "reasons": data["caution_day"]["reasons"]},
        "compat": [{"name": c["sign"]["name"], "score": c["score"], "comment": c["comment"]} for c in data["compat"]],
        "moon_events": [{"date": ymd_ja(e["date"]), "kind": e["kind"]} for e in data["moon_events"]],
        "sub_theme": data["sub_theme"],
        "keywords": data["keywords"],
        "action": data["action"],
        "lucky_word": data["lucky_word"],
        "lucky": {"color": data["color"], "item": data["item"], "place": data["place"]},
    }


# ───────────────────────── テンプレート（APIキーが無いときの文章） ─────────────────────────

def _fallback_weeklyish(product: str, data: dict) -> dict:
    sign = data["sign"]
    theme = data["sub_theme"]
    best, second = data["best_days"][0], data["best_days"][-1]
    caution = data["caution_day"]
    rng = _rng(data, product)
    span = {"intensive": "この2週間", "daily": "この日", "weekly": "この一週間"}.get(product, "この一週間")

    intro = (
        f"{sign['name']}のあなたへ。{sign['love_style']}\n\n"
        f"{span}、あなたの恋には「{data['keywords'][0]}」というテーマが流れています。"
        f"{sign['name']}を司る{sign['ruling_planet']}は、{'と'.join(sign['keywords'][:2])}をつかさどる星。"
        f"その力が、人との距離の取り方に静かに働きかけます。\n\n"
        f"誰かを思う気持ちは、強いときほど言葉にしづらくなります。"
        f"{span}は、言えずにいたことが、ふとした拍子に形になりやすい時期です。"
        f"焦って動くより、{md_wd(best['date'])}のように流れの整った日を選ぶほうが、同じ言葉でも届き方が変わります。"
    )

    flow_parts = [
        f"{span}の恋愛運は、平均すると星{round(data['average'])}つ分の巡りです。",
    ]
    if data["moon_events"]:
        event = data["moon_events"][0]
        flow_parts.append(
            f"{ymd_ja(event['date'])}には{event['kind']}を迎えます。"
            + ("新月は、新しい関係や、言いそびれていた気持ちを動かすのに向くとされる日です。"
               if event["kind"] == "新月"
               else "満月は気持ちが満ちる日。受け取るものと、手放すものがはっきりしやすくなります。")
        )
    flow_parts.append(
        f"流れが良いのは{md_wd(best['date'])}と{md_wd(second['date'])}。"
        f"反対に{md_wd(caution['date'])}は、言葉が強く出やすいので、"
        "返事を急がず一日置くくらいがちょうどよさそうです。"
    )
    flow_parts.append(
        f"{sign['element']}のエレメントを持つ{sign['name']}は、"
        + {"火": "勢いがあるときほど相手の反応を待てなくなります。半歩だけ引く意識を。",
           "地": "安心できる関係を好むぶん、変化を怖がりすぎることがあります。小さな新しさを一つだけ。",
           "風": "言葉が軽やかに出る時期です。軽さの奥にある本音も、ときどき見せてみてください。",
           "水": "相手の気持ちを感じ取りすぎて疲れやすい時期。自分の気持ちを先に確かめてから動きましょう。"}[sign["element"]]
    )
    flow = "\n\n".join(flow_parts)

    best_text = (
        f"{ymd_ja(best['date'])}は、{span}でもっとも恋が動きやすい日です。"
        f"{'／'.join(best['reasons']) if best['reasons'] else '暦が穏やかに整っています'}。"
        f"{ROKUYO_HINT.get(best['ko']['rokuyo'], '流れの整う日')}でもあります。\n\n"
        f"この日は「{data['action']}」が効きます。大げさなことをする必要はありません。"
        "相手の名前を呼ぶ、ひとこと多く返す、その程度の違いが、この日は大きく響きます。\n\n"
        f"続いて流れが良いのが{ymd_ja(second['date'])}。"
        "一度で伝わらなくても、日を変えてもう一度だけ声をかけてみてください。"
        "同じ言葉でも、受け取る側に余裕があるかどうかで、返ってくる反応は変わります。"
    )

    scenes = "\n\n".join([
        "■ 片思いの方",
        f"{sign['name']}のあなたは、{sign['love_style']}"
        f"だからこそ、{span}は「伝え方」より「伝える日」を選ぶことが効きます。"
        f"{md_wd(best['date'])}に短い連絡を一通。長い文より、相手が返しやすい軽さを意識してみてください。",
        "相手の反応が薄くても、それは気持ちがないという意味ではありません。"
        f"{md_wd(caution['date'])}のように巡りが重い日は、誰でも言葉が少なくなります。日を改めるだけで景色が変わります。",
        "■ 交際中の方",
        f"関係が安定しているぶん、言葉が減りやすい時期です。「{data['lucky_word']}」を、"
        "改めて声に出してみてください。当たり前になっていたことが、もう一度うれしいことに戻ります。",
        f"{theme['label']}で気を取られることがあっても、{md_wd(best['date'])}だけは相手の時間を優先してみる。"
        "その一日が、後から効いてきます。",
        "■ 復縁を考えている方",
        f"急ぐと空回りしやすい巡りです。動くなら{md_wd(best['date'])}以降。"
        "謝罪や説明から入るより、相手の近況をたずねるところから始めるほうが、会話が続きます。",
        "戻るか戻らないかを、今すぐ決める必要はありません。"
        f"{span}は、気持ちの置きどころを確かめる時間だと考えてみてください。",
    ])

    if product == "intensive":
        half = data["days"][7]["date"]
        scenes += "\n\n" + "\n\n".join([
            "■ 前半と後半の使い分け",
            f"前半（〜{md_wd(data['days'][6]['date'])}）は、相手の様子をうかがう時間にあてるのが向いています。"
            "連絡の間隔、返事の長さ、話題の選び方。そうした小さなところに、相手の今の余裕が表れます。",
            f"後半（{md_wd(half)}〜）は、前半で感じ取ったことをもとに動く時間です。"
            f"{md_wd(best['date'])}のように流れの良い日を選べば、同じ言葉でも受け取られ方が変わります。",
            "■ 迷ったときの判断の仕方",
            f"{sign['name']}のあなたは、{sign['love_keywords'][0]}を大切にする人です。"
            "相手に合わせすぎて、自分がどうしたいか分からなくなったときは、次の順番で考えてみてください。",
            "まず「自分はこの関係をどうしたいか」。次に「そのために今週できる一番小さなことは何か」。"
            "最後に「それをいつやるか」。この三つが決まれば、迷う時間はぐっと減ります。",
            "■ うまくいかない日の過ごし方",
            f"{md_wd(caution['date'])}のように巡りの重い日は、誰にでもあります。"
            "そういう日は、相手のことを考える時間をいったん手放して、自分の生活を整えるほうに使ってください。"
            f"部屋を片づける、早く眠る、{data['item']}を手に取る。それだけで、翌日の言葉はやわらかくなります。",
        ])

    compat_note = (
        f"{span}、{sign['name']}と響き合いやすいのは"
        + "、".join(c["sign"]["name"] for c in data["compat"]) + "です。\n\n"
        + data["compat"][0]["comment"] + "\n\n"
        "相性は、合う・合わないを決めつけるためのものではありません。"
        "相手のリズムが自分と違うと分かっているだけで、沈黙や間の取り方を責めずに済みます。"
        "相性表に名前がない星座の相手でも、違いを面白がれる関係は長く続きます。"
    )

    sub_theme = (
        f"恋愛だけが毎日ではありません。{span}は{theme['lead']}が、ふとした瞬間に気になりそうです。\n\n"
        f"{sign['name']}はもともと{sign['keywords'][0]}を持つ星座。その強みは、{theme['advice_focus']}にもそのまま使えます。"
        f"ただ、気を張る時間が続くと、恋愛に向ける余力がなくなります。"
        f"{md_wd(caution['date'])}あたりで、一度立ち止まってみてください。\n\n"
        f"うまくいかない日は、自分を責めるのではなく「今回はそういう巡りだった」と切り分けること。"
        f"{md_wd(best['date'])}は人に相談するにも良い日です。ひとりで抱えなくて大丈夫です。"
    )

    closing = rng.choice([
        f"恋は、タイミングだけで決まるものではありません。それでも「今日は動いてみよう」と思える日が分かっていると、"
        f"迷う時間は短くなります。{sign['name']}のあなたが持っている{sign['keywords'][0]}は、"
        "焦らずに出したときにいちばん伝わります。",
        f"月が満ちて欠けるように、関係にも波があります。良い日に動き、静かな日には整える。"
        f"{span}をそんなふうに過ごせたら、それだけで十分です。"
        f"{sign['name']}のあなたらしい{sign['love_keywords'][0]}を、どうか大切にしてください。",
    ]) + f"\n\n{span}が、あなたにとって穏やかな時間になりますように。"

    return {"intro": intro, "flow": flow, "best_days": best_text, "scenes": scenes,
            "compat_note": compat_note, "sub_theme": sub_theme, "closing": closing}


def _fallback_summary(rows: list, start, end) -> dict:
    top = rows[0]
    theme = top["sub_theme"]
    intro = (
        f"{ymd_ja(start)}から{ymd_ja(end)}までの恋愛運を、12星座すべて占いました。\n\n"
        f"この期間でいちばん恋が動きやすいのは{top['sign']['name']}。"
        f"キーワードは「{top['keywords'][0]}」です。とはいえ、順位はあくまで巡りの話。"
        "下のほうにいる星座も、静かに整える時間と考えれば損ではありません。"
    )
    flow_parts = [f"この期間の暦を見ると、{ymd_ja(top['best_days'][0]['date'])}あたりに流れの良い日が集まっています。"]
    if top["moon_events"]:
        event = top["moon_events"][0]
        flow_parts.append(f"{ymd_ja(event['date'])}は{event['kind']}。"
                          + ("始まりに向く日です。" if event["kind"] == "新月" else "気持ちが満ちる日です。"))
    flow_parts.append(f"今回の暮らしのテーマは「{theme['label']}」。{theme['lead']}が気になりやすい時期でもあります。")
    closing = (
        "順位が高い星座も低い星座も、やることは同じです。流れの良い日に一歩だけ動いて、"
        "重たい日は無理をしない。それだけで、関係の景色は少しずつ変わっていきます。\n\n"
        "星座別のくわしい運勢は、それぞれの記事で読めます。"
    )
    return {"intro": intro, "flow": "\n\n".join(flow_parts), "closing": closing}


# ───────────────────────── 生成 ─────────────────────────

def narrate(product: str, data=None, rows=None, start=None, end=None) -> dict:
    spec = SPECS[product]
    if product == "summary":
        base = _fallback_summary(rows, start, end)
        facts = {"period": f"{ymd_ja(start)}〜{ymd_ja(end)}",
                 "ranking": [{"rank": i, "name": r["sign"]["name"], "score": round(r["average"], 1),
                              "keyword": r["keywords"][0]} for i, r in enumerate(rows, 1)],
                 "sub_theme": rows[0]["sub_theme"],
                 "moon_events": [{"date": ymd_ja(e["date"]), "kind": e["kind"]} for e in rows[0]["moon_events"]]}
    else:
        base = _fallback_weeklyish(product, data)
        facts = build_facts(product, data)

    try:
        client = GeminiClient()
    except ValueError as e:
        logger.info(f"テンプレート文を使用します（{e}）")
        return base

    keys = json.dumps({k: f"{v[0]}〜{v[1]}字" for k, v in spec.items()}, ensure_ascii=False, indent=1)
    prompt = PROMPT.format(keys=keys, facts=json.dumps(facts, ensure_ascii=False, indent=1))
    try:
        generated = client.generate_json(prompt)
    except Exception as e:
        logger.warning(f"文章生成に失敗したためテンプレート文を使用します: {e}")
        return base

    out = dict(base)
    for key, (low, high) in spec.items():
        text = generated.get(key) if isinstance(generated, dict) else None
        if not isinstance(text, str) or not low * 0.7 <= len(text) <= high * 1.5:
            logger.warning(f"{product}/{key}: 長さが合わないためテンプレート文を使用します")
            continue
        out[key] = text.strip()
    return out
