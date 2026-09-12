"""読みものとしての解説文（導入・暦の由来・データの読み解き・予想の性格づけ）

数値はすべて計算結果から差し込む。言い回しは回号ごとに決まる乱数で選ぶので、
同じ回なら何度生成しても同じ文章になり、回ごとには表現が変わる。
"""

import random
import zlib

from src.analysis.numbers import pattern_of
from src.config import FEATURE_LABELS, FEATURE_SHORT, FEATURES
from src.utils.dates import to_date, ymd_ja

SEASON = {
    1: "新しい年の空気がまだ残る1月", 2: "寒さの底から春の兆しが見えはじめる2月",
    3: "日差しが少しずつやわらぐ3月", 4: "新しい季節が動き出す4月",
    5: "若葉がまぶしい5月", 6: "雨が大地をうるおす6月",
    7: "夏の勢いが増していく7月", 8: "真夏の熱気に包まれる8月",
    9: "秋の気配が少しずつ深まる9月", 10: "実りの秋を迎える10月",
    11: "冬の足音が近づく11月", 12: "一年の締めくくりを迎える12月",
}

# (意味, 数字選びへの使い方) いずれも「日」で終わる
ROKUYO_DETAIL = {
    "大安": ("六曜の中でもっとも吉とされ、一日を通して何事も穏やかに進めやすい日",
             "時間帯を気にせず、落ち着いて数字を決められる日"),
    "友引": ("勝負ごとが「引き分け」になるとも言われ、朝と夕方が吉、正午前後は凶とされる日",
             "数字を最終的に決めるなら、朝か夕方がよいとされる日"),
    "先勝": ("「先んずれば即ち勝つ」の意味を持ち、午前中が吉、午後は凶とされる日",
             "数字選びは午前中のうちに済ませる、という暦の使い方ができる日"),
    "先負": ("「先んずれば即ち負ける」の意味を持ち、急がず静かに過ごすのがよく、午後が吉とされる日",
             "焦らず、午後になってからゆっくり数字を決めるのが暦らしい日"),
    "赤口": ("正午前後（11時〜13時ごろ）だけが吉とされる、慎重さが大切な日",
             "お昼どきに数字を決めるのが、暦に沿った楽しみ方になる日"),
    "仏滅": ("「物が滅して新たに始まる」とも解釈され、区切りや仕切り直しに向くとされる日",
             "これまでの選び方をいったんリセットして、新しい視点で数字を見るのにぴったりの日"),
}

KYUSEI_DETAIL = {
    1: "一白水星は「水」の星。流れに逆らわず形を変えるしなやかさと、人と人をつなぐ力を象徴します。",
    2: "二黒土星は「大地」の星。コツコツと積み上げる堅実さと、ものを育てる包容力を象徴します。",
    3: "三碧木星は「雷」と「若木」の星。勢いよく伸びていく発展の力と、新しいことを始めるエネルギーを象徴します。",
    4: "四緑木星は「風」の星。遠くまで運ばれていくご縁と、物事をととのえる力を象徴します。",
    5: "五黄土星は九星の中心に座る「帝王」の星。物事を大きく動かす、強い力を象徴します。",
    6: "六白金星は「天」の星。高い理想と向上心、大きな目標へ向かう力を象徴します。",
    7: "七赤金星は「沢」の星。喜びや豊かさ、実りを楽しむ心を象徴します。",
    8: "八白土星は「山」の星。変化の節目と、蓄えたものを守り育てる力を象徴します。",
    9: "九紫火星は「火」の星。ひらめきや華やかさ、物事を明るく照らす力を象徴します。",
}

JIKKAN_DETAIL = {"甲": "大樹", "乙": "草花", "丙": "太陽", "丁": "灯火", "戊": "山",
                 "己": "田畑", "庚": "鉄や刀剣", "辛": "宝石", "壬": "大海", "癸": "雨露"}
JUNISHI_DETAIL = {"子": "物事の始まりと繁栄", "丑": "粘り強さと蓄え", "寅": "決断と勢い", "卯": "穏やかな飛躍",
                  "辰": "大きな変化と上昇", "巳": "再生と豊かさ", "午": "活力と前進", "未": "安定と調和",
                  "申": "機転と実り", "酉": "収穫の喜び", "戌": "誠実さと守り", "亥": "エネルギーの蓄え"}

LUCKY_DETAIL = {
    "天赦日": "天がすべてを赦すとされる、暦の上で最上の吉日。年に数回しかめぐってこない特別な日です。",
    "一粒万倍日": "一粒の籾が万倍にも実るとされる日。何かを始めるのに良いとされ、宝くじを買う日に選ぶ人も多い吉日です。",
    "寅の日": "寅は「千里行って千里帰る」とされ、出ていったものが戻ってくる、金運にご縁のある日と言われます。",
    "巳の日": "巳（へび）は弁財天の使いとされ、金運や財運にご縁のある日と言われます。",
    "己巳の日": "60日に一度めぐる、巳の日の中でも特に弁財天とのご縁が深いとされる日です。",
    "甲子の日": "六十干支のはじまりの日。物事を始めるのに良いとされ、大黒天の縁日でもあります。",
}

RELATION_ADVICE = {
    "比和": "こういう日は、データと暦で“重なった数字”を素直に信じる選び方が合っています。",
    "相生": "こういう日は、本命を軸にして、対抗へと自然に広げていく選び方が合っています。",
    "相剋": "こういう日は、本命だけに寄せず、穴の視点も少し混ぜてバランスを取る選び方が合っています。",
}

FEATURE_STORY = {
    "hot": "最近よく出ている数字が、そのまま勢いを保った",
    "trend": "ここにきて出現ペースを上げてきた数字が伸びた",
    "cold": "しばらく姿を見せていなかった数字が戻ってきた",
    "carry": "前回と同じ数字が、続けて顔を出した",
    "slide": "前回の数字の“お隣さん”が選ばれた",
    "koyomi": "抽せん日の暦と重なる数字が、出目に絡んだ",
}
FEATURE_STORY_NEG = {
    "hot": "人気の数字はひと休みしていました",
    "trend": "勢いのあった数字は少し失速しました",
    "cold": "出ていない数字は、そのまま沈黙を続けました",
    "carry": "前回の数字はほとんど続きませんでした",
    "slide": "お隣の数字への流れは起きませんでした",
    "koyomi": "暦の数字は、今回は出目にあまり絡みませんでした",
}

HOOK_OPENERS = [
    "数字選択式の宝くじは、毎回まったくの無作為で数字が決まります。それでも「なぜこの数字を選んだのか」を自分の中に持てると、抽せんを待つ時間はぐっと楽しくなるものです。",
    "「どうせ運だから」と思いつくままに数字を並べるのも、ひとつの楽しみ方です。でも、せっかくなら一つひとつの数字に理由を持たせてみると、結果が出るまでのワクワクがまったく違ってきます。",
    "誕生日、記念日、なんとなく好きな数字。数字の選び方は人それぞれですが、ここでは「過去のデータ」と「暦の知恵」という二つの物差しを使って、じっくり数字を選んでいきます。",
]
REVIEW_CLOSERS = [
    "もちろん、一週間の結果だけで「この見方が正しい」と決めつけることはできません。抽せんは毎回リセットされる無作為の世界。だからこそ、良かった点もそうでなかった点も、記録として淡々と積み上げていくことに意味があると考えています。",
    "結果に一喜一憂するよりも、「先週の出目はどんな性格だったのか」を知ることが、次の数字選びのヒントになります。この回顧は、そのための大切な作業です。",
    "数字の世界に確かな答えはありません。それでも、一週間ごとの出目の“性格”を丁寧に記録していくと、少しずつ見えてくるものがあります。",
]
REFLECT_OPENERS = [
    "天気予報が毎日の観測データで少しずつ精度を磨いていくように、このノートの数字選びも毎週アップデートしています。",
    "料理の味見をしながら塩加減をととのえるように、このモデルも毎週、結果を見ながら分析軸のバランスを調整しています。",
    "先週の結果は、今週の数字選びにとって何よりの教材です。うまくいった見方は少し強く、うまくいかなかった見方は少し控えめに――。",
]
CLOSERS = [
    "数字選択式の宝くじは、どれだけ分析を重ねても、結果は毎回無作為に決まります。だからこそ、根拠を持って選んだ数字を、生活に無理のない金額で、ワクワクしながら楽しむのがいちばんです。",
    "宝くじの楽しさは、抽せんを待つ時間そのものにもあります。自分なりの理由を持って選んだ数字なら、その時間はきっといつもより少し特別なものになるはずです。もちろん、購入は無理のない範囲で。",
]

TIER_INTRO = {
    "本命": "本命は、今週の重みで計算した総合スコアをもとに、合計値や奇数・偶数のバランスが歴史的に多い形に収まる組み合わせだけを選んだ“王道”です。",
    "対抗": "対抗は、暦の比重を2倍にして組み直した組み合わせ。抽せん日の暦との重なりを大切にした、このノートらしい“暦寄り”の選び方です。",
    "穴": "穴は、未出現期間の長い数字を重く見た組み合わせ。本命とは違う角度から、しばらく眠っている数字の目覚めに備えます。",
}


def rng_for(key: str, draw: int) -> random.Random:
    return random.Random(zlib.crc32(f"text-{key}-{draw}".encode()))


def _n(n: int) -> str:
    return f"{n:02d}"


def _nums(ns) -> str:
    return " ".join(_n(n) for n in ns)


def _lift(t: dict) -> float:
    return (t["hits"] - t["baseline"]) / t["baseline"] if t["baseline"] else 0.0


def _names(ctxs: list) -> str:
    return "・".join(x["game"].name for x in ctxs)


# ───────────────────────── 無料部分 ─────────────────────────

def hook(series_key: str, ctxs: list) -> str:
    c = ctxs[0]
    ko = c["ko"]
    d = to_date(c["date"])
    rng = rng_for(series_key, c["draw"])
    if ko["lucky_days"]:
        mood = f"「{ko['rokuyo']}」に「{'」「'.join(ko['lucky_days'])}」が重なる、数字選びにも前向きな気持ちで向き合える一日です。"
    else:
        mood = f"六曜は「{ko['rokuyo']}」、日の星は{ko['kyusei_name']}。静かに、じっくりと数字と向き合える一日です。"
    unit = "各10パターン" if series_key == "numbers" else "10口"
    totals = "、".join(f"{x['game'].name}全{x['analysis']['total']:,}回分" for x in ctxs)

    paragraphs = [
        f"{SEASON[d.month]}。{ymd_ja(d)}の{_names(ctxs)}は、暦を開くと{mood}",
        rng.choice(HOOK_OPENERS),
        f"このノートでは、{totals}の当せん番号を統計で読み解き、そこに六曜・九星・干支・数秘といった暦の視点を重ねて、今回の{unit}を選んでいます。"
        "データだけでも、占いだけでもない。性格のまったく違う二つの物差しが同じ数字を指したとき、その数字には少し特別な意味が生まれる――そんな考え方で組み立てています。",
        "そしてもう一つ大切にしているのが「振り返り」です。毎週、先週の予想が実際の結果とどう違ったのかを正直に検証し、"
        "その学びを今週の数字選びにどう反映したのかまで、包み隠さず公開しています。",
    ]
    extra = []
    for x in ctxs:
        game, last = x["game"], x["last"]
        if game.kind == "loto":
            carryover = last.get("carryover") or 0
            if carryover >= 1e8:
                extra.append(f"今回の{game.name}は、前回からキャリーオーバーが約{carryover / 1e8:.1f}億円。いつも以上に注目が集まる回です。")
        else:
            extra.append(f"{game.name}の前回（第{last['draw']}回）は「{last['number']}」（{pattern_of(last['number'])}）でした。")
    if extra:
        paragraphs.append("".join(extra))
    return "\n\n".join(paragraphs)


def koyomi_teaser(ko: dict) -> str:
    meaning, _ = ROKUYO_DETAIL[ko["rokuyo"]]
    text = f"今回の「{ko['rokuyo']}」は、{meaning}です。"
    for day in ko["lucky_days"]:
        text += f"さらにこの日は「{day}」。{LUCKY_DETAIL[day]}"
    text += f"日の星・{ko['kyusei_name']}と、日の干支「{ko['kanshi']}」がどんな数字と響き合うのかは、有料部分の暦分析でじっくり読み解いています。"
    return text


def review_story(series_key: str, ctxs: list) -> str:
    rng = rng_for(series_key, ctxs[0]["draw"])
    paragraphs = []
    for x in ctxs:
        game, reviews, wk = x["game"], x["review_prev"], x["weekly"]
        if not reviews:
            continue
        prized = [rv for rv in reviews if rv["best"]["prize"]]
        if game.kind == "loto":
            if prized:
                rv = prized[0]
                s = f"{game.name}では、第{rv['draw']}回で{rv['best']['prize']}相当の組み合わせが10口の中に入っていました。"
            else:
                rv = max(reviews, key=lambda r: (r["best"]["matches"], r["best"]["bonus"]))
                m = rv["best"]["matches"]
                lead = "いちばん惜しかったのは" if m >= 3 else "いちばん重なりが多かったのは"
                s = f"{game.name}で{lead}第{rv['draw']}回。10口の中で、当せん数字と最大{m}個が重なりました。"
        else:
            if prized:
                rv = prized[0]
                s = f"{game.name}では、第{rv['draw']}回（当せん番号「{rv['result']['number']}」）で{rv['best']['prize']}の形をとらえたパターンがありました。"
            else:
                rv = max(reviews, key=lambda r: r["best"]["positions"])
                s = f"{game.name}でいちばん惜しかったのは第{rv['draw']}回（当せん番号「{rv['result']['number']}」）。位置まで一致した数字が{rv['best']['positions']}桁ありました。"
        if wk["draws"]:
            lifts = {f: _lift(wk["totals"][f]) for f in FEATURES}
            top = max(FEATURES, key=lambda f: lifts[f])
            low = min(FEATURES, key=lambda f: lifts[f])
            s += (
                f"分析軸で見ると、先週は「{FEATURE_SHORT[top]}」が期待値を上回りました。言いかえると、{FEATURE_STORY[top]}一週間だったということです。"
                f"反対に「{FEATURE_SHORT[low]}」は振るわず、{FEATURE_STORY_NEG[low]}。"
            )
        paragraphs.append(s)
    paragraphs.append(rng.choice(REVIEW_CLOSERS))
    if any(rv["backtest"] for x in ctxs for rv in x["review_prev"]):
        paragraphs.append("※先週分は、このノートの公開前の回を、その時点までのデータだけで計算し直した検証結果です。")
    return "\n\n".join(paragraphs)


def reflection_story(series_key: str, ctxs: list) -> str:
    rng = rng_for(series_key, ctxs[0]["draw"] + 1)
    moves = []
    for x in ctxs:
        wk = x["weekly"]
        if not wk["draws"]:
            continue
        delta = {f: wk["after"][f] - wk["before"][f] for f in FEATURES}
        up = max(FEATURES, key=lambda f: delta[f])
        down = min(FEATURES, key=lambda f: delta[f])
        moves.append(
            f"{x['game'].name}では、先週の結果を受けて「{FEATURE_LABELS[up]}」の比重を{wk['before'][up] * 100:.1f}%から{wk['after'][up] * 100:.1f}%へ引き上げ、"
            f"「{FEATURE_LABELS[down]}」は{wk['before'][down] * 100:.1f}%から{wk['after'][down] * 100:.1f}%へ控えめにしました。"
        )
    if not moves:
        return "先週は対象の抽せんがなかったため、分析軸の重みは据え置きのまま、今回の数字を計算しています。"
    return "\n\n".join([
        rng.choice(REFLECT_OPENERS),
        "".join(moves),
        "ただし、たった一週間の結果で考え方を大きく変えてしまうと、偶然の波に振り回されてしまいます。"
        "そこで、一度に動かす幅には上限を設け、どの分析軸も5%〜40%の範囲に収まるようにしています。"
        "急がず、でも着実に、最近の出目のクセに寄せていく――それがこのノートの基本姿勢です。今回の本命・対抗・穴は、すべてこの新しいバランスで計算しました。",
    ])


def free_data_comment(ctx: dict) -> str:
    game, a = ctx["game"], ctx["analysis"]
    if game.kind == "loto":
        if a["chi_p"] >= 0.05:
            s = (
                f"少し意外かもしれませんが、{game.name}の全{a['total']:,}回分を統計的に検定しても、特定の数字だけが極端に出やすいという“えこひいき”は見つかりません。"
                "だからこそ、長期のデータだけでなく「直近の流れ」や「暦との重なり」といった、別の角度からの物差しが意味を持ってきます。"
            )
        else:
            s = f"{game.name}の全{a['total']:,}回分を検定すると、数字ごとの出やすさに統計的な偏りが見られます。長期の傾向も、今回の点数づけにしっかり取り入れています。"
        s += f"また、6つ（または7つ・5つ）の数字の合計値は、全体の8割が{a['sum_lo']}〜{a['sum_hi']}に収まっています。小さい数字ばかり、大きい数字ばかりの組み合わせは、歴史的にはかなり珍しい形なんです。"
        return s.replace("6つ（または7つ・5つ）", f"{game.pick}つ")
    patterns = dict(a["pattern_all"])
    if game.digits == 4:
        return (
            f"ナンバーズ4では、全{a['total']:,}回のうち約{patterns.get('シングル', 0):.0%}が4つとも違う数字の「シングル」、"
            f"約{patterns.get('ダブル', 0):.0%}が同じ数字を2つ含む「ダブル」でした。"
            "「同じ数字が入る形は出にくい」と感じる方も多いと思いますが、ダブルは実は2回に1回近く出ている、とても身近なパターンです。"
        )
    return (
        f"ナンバーズ3では、約{patterns.get('シングル', 0):.0%}が3つとも違う数字の「シングル」、約{patterns.get('ダブル', 0):.0%}が「ダブル」。"
        "シングルが主役ではあるものの、ダブルも決して珍しくない形です。"
    )


def paid_highlight(series_key: str, ctxs: list) -> str:
    items = []
    for x in ctxs:
        game, a, p = x["game"], x["analysis"], x["pred"]
        if game.kind == "loto":
            hot, cold = a["hot"][0], a["cold"][0]
            item = f"{game.name}の直近20回で{a['f20'][hot]}回も顔を出している“いま最も勢いのある数字”、{a['interval'][cold]}回連続で姿を見せていない“沈黙の数字”"
            overlap = {r["n"] for r in p["top"]} & set(p["koyomi_numbers"])
            if overlap:
                item += f"、そしてデータと暦の両方で上位に入った“重なり数字”が{len(overlap)}つ"
        else:
            best = max(a["positions"], key=lambda pos: pos["f30"][pos["hot"][0]])
            longest = max(a["positions"], key=lambda pos: pos["interval"][pos["cold"][0]])
            item = (
                f"{game.name}の{best['label']}で直近30回に{best['f30'][best['hot'][0]]}回も出ている数字、"
                f"{longest['label']}で{longest['interval'][longest['cold'][0]]}回も沈黙を続けている数字"
            )
        items.append(item)
    unit = "各10パターン" if series_key == "numbers" else "10口"
    return (
        "有料部分では、ここからさらに踏み込みます。" + "。".join(items) + "――。"
        f"それぞれがどの数字なのか、そして{unit}のどこにどう組み込んだのかを、データの読み解きと暦の解説とともにすべて公開しています。"
    )


# ───────────────────────── 有料部分：暦 ─────────────────────────

def koyomi_reading(ko: dict) -> str:
    kan, shi = ko["kanshi"][0], ko["kanshi"][1]
    meaning, advice = ROKUYO_DETAIL[ko["rokuyo"]]
    paragraphs = [
        f"まずは六曜から。今回の「{ko['rokuyo']}」は、{meaning}です。数字選びに当てはめるなら、{advice}と言えます。",
        f"日の九星は{ko['kyusei_name']}。{KYUSEI_DETAIL[ko['kyusei']].split('は', 1)[1]}",
        f"日の干支は「{ko['kanshi']}」。十干の「{kan}」は自然にたとえると“{JIKKAN_DETAIL[kan]}”、十二支の「{shi}」は{JUNISHI_DETAIL[shi]}を表します。",
    ]
    if ko["lucky_days"]:
        paragraphs.append(
            "そしてこの日は" + "・".join(f"「{d}」" for d in ko["lucky_days"]) + "にあたります。"
            + "".join(LUCKY_DETAIL[d] for d in ko["lucky_days"])
        )
    paragraphs.append(
        f"五行で見ると、日の干は「{ko['day_gogyo']}」、日の星は「{ko['kyusei_gogyo']}」で、両者は{ko['relation']}の関係。"
        f"{ko['relation_text']}です。{RELATION_ADVICE[ko['relation']]}"
    )
    paragraphs.append(
        f"数秘では、日付の数字をすべて足すと「{ko['numerology']}」。ここに九星の数と五行の数（河図の数）を合わせて、"
        f"今回の暦のラッキーデジットを「{'・'.join(map(str, ko['lucky_digits']))}」としました。"
        "暦の数字は、データの傾向と重ねて“迷ったときの決め手”として使うのがおすすめです。"
    )
    return "\n\n".join(paragraphs)


def closing_message(series_key: str, ctxs: list) -> str:
    ko = ctxs[0]["ko"]
    rng = rng_for(series_key, ctxs[0]["draw"] + 2)
    _, advice = ROKUYO_DETAIL[ko["rokuyo"]]
    return "\n\n".join([
        f"最後に、暦からのひとことを。{ko['rokuyo']}の今回は、{advice}です。"
        f"五行は{ko['relation']}、{ko['relation_text']}。{RELATION_ADVICE[ko['relation']]}",
        rng.choice(CLOSERS),
        "このノートでは毎回、抽せん結果が出たあとに必ず振り返りを行い、その学びを次の数字選びにつなげていきます。"
        "うまくいった回も、惜しかった回も、次の記事で一緒に見届けていただけたらうれしいです。",
        f"{_names(ctxs)}の抽せんが、あなたにとって楽しい時間になりますように。",
    ])


# ───────────────────────── 有料部分：ロト系の読み解き ─────────────────────────

def loto_hot_comment(ctx: dict) -> str:
    a = ctx["analysis"]
    n = a["hot"][0]
    strong = sorted(x for x, z in a["z100"].items() if z >= 2)
    s = f"トップの{_n(n)}は直近20回で{a['f20'][n]}回。期待値{a['e20']:.1f}回の約{a['f20'][n] / a['e20']:.1f}倍というペースで、いまもっとも勢いのある数字です。"
    if strong:
        s += f"直近100回で見ても{_nums(strong)}はz値が2を超えており、一時的な偶然というより、しばらく続いている流れと言えそうです。"
    else:
        s += "ただし直近100回まで広げると、z値が2を超える数字はありません。長い目で見れば“ほどよい偏り”の範囲です。短期の勢いと長期の落ち着き、その両方を見ながら点数をつけています。"
    return s


def loto_cold_comment(ctx: dict) -> str:
    a = ctx["analysis"]
    n = a["cold"][0]
    interval = a["interval"][n]
    return (
        f"もっとも長く眠っているのは{_n(n)}で、{interval}回連続の未出現。平均的な出現間隔（約{a['mean_gap']:.1f}回）の、およそ{interval / a['mean_gap']:.1f}倍にあたります。"
        "「そろそろ出るはず」と考えたくなるところですが、抽せん機に記憶はありません。"
        "このノートでは“出ていない”こと自体を数字の個性として点数化し、特に穴の組み合わせで活かしています。"
    )


def loto_shape_comment(ctx: dict) -> str:
    a = ctx["analysis"]
    recent_avg = sum(a["recent_sums"]) / len(a["recent_sums"])
    diff = recent_avg - a["sum_mean"]
    if diff > a["sum_std"] * 0.3:
        s = f"直近10回の合計値の平均は{recent_avg:.0f}で、全回平均（{a['sum_mean']:.0f}）より高め。大きめの数字が続けて選ばれている流れです。"
    elif diff < -a["sum_std"] * 0.3:
        s = f"直近10回の合計値の平均は{recent_avg:.0f}で、全回平均（{a['sum_mean']:.0f}）より低め。小さめの数字が続いている流れです。"
    else:
        s = f"直近10回の合計値の平均は{recent_avg:.0f}で、全回平均（{a['sum_mean']:.0f}）とほぼ同じ。極端な偏りのない、落ち着いた流れです。"
    odd_all, odd_20 = a["odd_top_all"][0][0], a["odd_top_20"][0][0]
    if odd_all != odd_20:
        s += f"奇数の個数は、全回では{odd_all}個がもっとも多い一方、直近20回では{odd_20}個が最多と、少し形が変わってきています。"
    else:
        s += f"奇数の個数は全回・直近20回とも{odd_all}個が最多で、ここは王道の形が続いています。"
    s += f"また「連続した数字は避けたほうがいい」と思われがちですが、実際にはおよそ{a['consec_all']:.0%}の回で連番が含まれています。"
    return s


def loto_pair_comment(ctx: dict) -> str:
    a = ctx["analysis"]
    (x, y), count = a["top_pairs"][0]
    return (
        f"直近100回でもっとも多く同時に出ているのは{_n(x)}と{_n(y)}の組み合わせで、{count}回。"
        f"偶然の期待値（約{a['pair_expected']:.1f}回）の約{count / a['pair_expected']:.1f}倍にあたる、いわば“相性のいいコンビ”です。"
        "組み合わせを考えるときの、小さなヒントとして参考にしています。"
    )


def loto_score_comment(ctx: dict) -> str:
    p = ctx["pred"]
    overlap = sorted(r["n"] for r in p["top"] if r["n"] in p["koyomi_numbers"])
    if overlap:
        s = f"データと暦、二つの物差しの両方で評価が高かったのは{_nums(overlap)}。性格の違う二つの見方が同じ方向を指した数字として、組み合わせの中心に置いています。"
    else:
        s = "今回は、データの上位と暦数字の重なりがありませんでした。二つの物差しが別々の方向を指した回です。そのぶん本命はデータ寄り、対抗は暦寄りと、組み合わせごとの性格をはっきり分けています。"
    s += f"軸数字の{_nums(p['axis'])}は総合スコアの上位3つ、除外候補の{_nums(p['exclude'])}は今回の重みではもっとも評価が低かった数字です。"
    return s


def choose_tag(tags: list, used: dict) -> str:
    """当てはまる性格のうち、この記事でいちばん使われていないもの（同数なら優先順）を選ぶ"""
    tag = min(tags, key=lambda t: used.get(t, 0))
    used[tag] = used.get(tag, 0) + 1
    return tag


def loto_pick_tags(pick: dict, ctx: dict) -> list:
    p, a = ctx["pred"], ctx["analysis"]
    c = p["constraints"]
    nums = set(pick["numbers"])
    ordered = sorted(nums)
    axis_n = len(nums & set(p["axis"]))
    ko_n = len(nums & set(p["koyomi_numbers"]))
    tags = []
    if axis_n >= 3:
        tags.append("軸数字を3つ抱えた、今回の王道型")
    if ko_n >= 4:
        tags.append("暦数字をたっぷり含んだ、暦寄り型")
    if nums & set(a["cold"][:3]):
        tags.append("長く眠っている数字を含む、変化に備える型")
    if nums & set(a["hot"][:3]):
        tags.append("いま勢いのある数字を含む、流れに乗る型")
    if axis_n == 2:
        tags.append("軸数字を2つ含んだ、安定感のある型")
    if pick["sum"] >= c["sum_hi"] - 15:
        tags.append("大きめの数字でまとめた、高合計型")
    if pick["sum"] <= c["sum_lo"] + 15:
        tags.append("小さめの数字でまとめた、低合計型")
    if any(y - x == 1 for x, y in zip(ordered, ordered[1:])):
        tags.append("連番を含んだ、実は出現の多い形")
    if ko_n >= 2:
        tags.append("暦数字をほどよく混ぜた型")
    if pick["odd"] >= 4:
        tags.append("奇数を多めにそろえた型")
    if pick["odd"] <= 2:
        tags.append("偶数を多めにそろえた型")
    tags.append("偏りの少ない、バランス型")
    return tags


# ───────────────────────── 有料部分：ナンバーズの読み解き ─────────────────────────

def numbers_position_comment(ctx: dict) -> str:
    a = ctx["analysis"]
    best = max(a["positions"], key=lambda pos: pos["f30"][pos["hot"][0]])
    g = best["hot"][0]
    longest = max(a["positions"], key=lambda pos: pos["interval"][pos["cold"][0]])
    g2 = longest["cold"][0]
    return (
        f"桁ごとに見ると、いま一番勢いがあるのは{best['label']}の「{g}」。直近30回で{best['f30'][g]}回、期待値3回の約{best['f30'][g] / 3:.1f}倍です。"
        f"反対に、もっとも長く沈黙しているのは{longest['label']}の「{g2}」で、{longest['interval'][g2]}回連続で出ていません。"
        "ナンバーズは桁ごとに数字が決まるため、このノートでは“桁ごとの個性”を別々に点数化しています。"
    )


def numbers_shape_comment(ctx: dict) -> str:
    game, a = ctx["game"], ctx["analysis"]
    all_p, recent_p = dict(a["pattern_all"]), dict(a["pattern_30"])
    d_all, d_recent = all_p.get("ダブル", 0), recent_p.get("ダブル", 0)
    tone = "多め" if d_recent - d_all > 0.05 else ("少なめ" if d_all - d_recent > 0.05 else "ほぼ平均どおり")
    s = f"直近30回ではダブルが{d_recent:.0%}で、全回の{d_all:.0%}と比べると{tone}です。"
    recent_avg = sum(a["recent_sums"]) / len(a["recent_sums"])
    diff = recent_avg - a["sum_mean"]
    trend = "高め" if diff > 1.5 else ("低め" if diff < -1.5 else "ほぼ同じ")
    s += f"数字の合計は直近10回の平均が{recent_avg:.1f}と、全回平均（{a['sum_mean']:.1f}）より{trend}。" if trend != "ほぼ同じ" else f"数字の合計は直近10回の平均が{recent_avg:.1f}と、全回平均（{a['sum_mean']:.1f}）とほぼ同じです。"
    s += f"前回と同じ桁に同じ数字が続けて出た回は、全回の{a['repeat_rate']:.0%}。{game.name}の予想では、こうした“形のクセ”も点数に反映しています。"
    return s


def numbers_score_comment(ctx: dict) -> str:
    a, p, ko = ctx["analysis"], ctx["pred"], ctx["ko"]
    agree = [(pos["label"], rows[0]["g"]) for pos, rows in zip(a["positions"], p["top"]) if rows[0]["g"] in ko["lucky_digits"]]
    if agree:
        return (
            "総合スコアの1位が暦のラッキーデジットと重なったのは、" + "、".join(f"{label}の「{g}」" for label, g in agree)
            + "。データと暦が同じ数字を指した桁として、本命の中心に置いています。"
        )
    return "今回は、どの桁でも総合1位と暦のラッキーデジットが重なりませんでした。データと暦が別々の数字を指した回なので、本命はデータ寄り、対抗は暦寄りと、性格をはっきり分けています。"


def numbers_pick_tags(pick: dict, ctx: dict) -> list:
    p, ko, a = ctx["pred"], ctx["ko"], ctx["analysis"]
    number = pick["number"]
    d = len(number)
    axis_hits = sum(int(ch) in axis for ch, axis in zip(number, p["axis"]))
    lucky = sum(int(ch) in ko["lucky_digits"] for ch in number)
    tags = []
    if pick["pattern"] != "シングル":
        tags.append(f"同じ数字を含む「{pick['pattern']}」で、出目の偏りに備える型")
    if axis_hits >= d - 1:
        tags.append("各桁の軸数字でまとめた、今回の王道型")
    if lucky >= d - 1:
        tags.append("暦のラッキーデジットを多く含んだ、暦寄り型")
    if pick["sum"] >= a["sum_hi"] - 2:
        tags.append("大きめの数字でまとめた、高合計型")
    if pick["sum"] <= a["sum_lo"] + 2:
        tags.append("小さめの数字でまとめた、低合計型")
    if axis_hits >= 1 and lucky >= 1:
        tags.append("データと暦をバランスよく混ぜた型")
    if axis_hits >= 2:
        tags.append("軸数字を半分ほど含んだ、安定感のある型")
    if lucky >= 2:
        tags.append("暦のラッキーデジットをほどよく含んだ型")
    tags.append("桁ごとの個性を組み合わせた、ばらつき型")
    return tags
