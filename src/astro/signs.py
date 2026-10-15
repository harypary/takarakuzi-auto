"""12星座のデータと相性（恋愛・人間関係に特化）"""

ZODIAC_SIGNS = [
    {"name": "牡羊座", "en": "aries", "symbol": "♈", "period": "3/21〜4/19", "element": "火", "modality": "活動",
     "ruling_planet": "火星", "keywords": ["情熱", "行動力", "開拓精神"],
     "love_keywords": ["ひと目惚れ", "まっすぐな好意", "追いかける恋"],
     "love_style": "好きになったら一直線。駆け引きより、まっすぐ伝えるほうが届きます。",
     "color": "朱赤", "item": "赤いリップ／スポーティな小物", "place": "開けた場所・スポーツ施設"},
    {"name": "牡牛座", "en": "taurus", "symbol": "♉", "period": "4/20〜5/20", "element": "地", "modality": "不動",
     "ruling_planet": "金星", "keywords": ["安定", "忍耐", "感覚美"],
     "love_keywords": ["安心感", "ゆっくり育つ愛", "五感で感じる"],
     "love_style": "時間をかけて信頼を育てるタイプ。急かされると心を閉じます。",
     "color": "アイボリー", "item": "上質なハンカチ／香り", "place": "静かなカフェ・美術館"},
    {"name": "双子座", "en": "gemini", "symbol": "♊", "period": "5/21〜6/21", "element": "風", "modality": "柔軟",
     "ruling_planet": "水星", "keywords": ["好奇心", "知性", "会話"],
     "love_keywords": ["言葉のやりとり", "軽やかさ", "共通の話題"],
     "love_style": "会話が合うかどうかがすべて。沈黙より、言葉数の多い関係が合います。",
     "color": "レモンイエロー", "item": "本／ペン", "place": "書店・にぎやかな街"},
    {"name": "蟹座", "en": "cancer", "symbol": "♋", "period": "6/22〜7/22", "element": "水", "modality": "活動",
     "ruling_planet": "月", "keywords": ["感受性", "家族愛", "守護"],
     "love_keywords": ["安心できる居場所", "思いやり", "手料理"],
     "love_style": "情の深さが魅力。相手を内側に入れると、とことん大切にします。",
     "color": "パールホワイト", "item": "手作りのもの／マグカップ", "place": "自宅・水辺"},
    {"name": "獅子座", "en": "leo", "symbol": "♌", "period": "7/23〜8/22", "element": "火", "modality": "不動",
     "ruling_planet": "太陽", "keywords": ["カリスマ", "創造性", "誇り"],
     "love_keywords": ["まっすぐな賞賛", "特別扱い", "堂々とした愛"],
     "love_style": "心から褒められると輝くタイプ。隠れた恋より、公にできる関係が合います。",
     "color": "ゴールド", "item": "華やかなアクセサリー", "place": "劇場・人の集まる場所"},
    {"name": "乙女座", "en": "virgo", "symbol": "♍", "period": "8/23〜9/22", "element": "地", "modality": "柔軟",
     "ruling_planet": "水星", "keywords": ["分析力", "献身", "誠実"],
     "love_keywords": ["小さな気遣い", "清潔感", "誠実さ"],
     "love_style": "細やかな気配りで愛を示します。言葉より行動を見てほしい人。",
     "color": "ネイビー", "item": "手帳／ハンドクリーム", "place": "整った空間・図書館"},
    {"name": "天秤座", "en": "libra", "symbol": "♎", "period": "9/23〜10/23", "element": "風", "modality": "活動",
     "ruling_planet": "金星", "keywords": ["調和", "美意識", "公平"],
     "love_keywords": ["対等な関係", "美しい時間", "さりげない気配り"],
     "love_style": "バランス感覚に優れた恋の名手。けれど本音を飲み込みがちです。",
     "color": "ペールピンク", "item": "花／香水", "place": "おしゃれなレストラン"},
    {"name": "蠍座", "en": "scorpio", "symbol": "♏", "period": "10/24〜11/22", "element": "水", "modality": "不動",
     "ruling_planet": "冥王星", "keywords": ["深層心理", "変容", "一途"],
     "love_keywords": ["深い結びつき", "一途さ", "秘密の共有"],
     "love_style": "一度決めた相手にはとことん。浅い関係では満たされません。",
     "color": "ワインレッド", "item": "黒い小物／香り", "place": "静かな夜の場所"},
    {"name": "射手座", "en": "sagittarius", "symbol": "♐", "period": "11/23〜12/21", "element": "火", "modality": "柔軟",
     "ruling_planet": "木星", "keywords": ["自由", "哲学", "冒険"],
     "love_keywords": ["自由な関係", "一緒に出かける", "笑える相手"],
     "love_style": "束縛を嫌う旅人。同じ方向を向いて走れる相手と長続きします。",
     "color": "ロイヤルブルー", "item": "旅のグッズ／スニーカー", "place": "遠出先・異国の雰囲気の店"},
    {"name": "山羊座", "en": "capricorn", "symbol": "♑", "period": "12/22〜1/19", "element": "地", "modality": "活動",
     "ruling_planet": "土星", "keywords": ["責任感", "野心", "現実主義"],
     "love_keywords": ["将来の約束", "信頼の積み上げ", "誠実な歩み"],
     "love_style": "恋にも計画性。遊びではなく、先を見据えた関係を求めます。",
     "color": "チャコールグレー", "item": "革小物／腕時計", "place": "落ち着いたバー・高台"},
    {"name": "水瓶座", "en": "aquarius", "symbol": "♒", "period": "1/20〜2/18", "element": "風", "modality": "不動",
     "ruling_planet": "天王星", "keywords": ["独創性", "友愛", "革新"],
     "love_keywords": ["友達のような恋人", "自由な距離感", "共鳴する価値観"],
     "love_style": "友情の延長に恋がある人。重い愛より、風通しのよい関係を好みます。",
     "color": "ターコイズ", "item": "ガジェット／変わった小物", "place": "イベント会場・新しい場所"},
    {"name": "魚座", "en": "pisces", "symbol": "♓", "period": "2/19〜3/20", "element": "水", "modality": "柔軟",
     "ruling_planet": "海王星", "keywords": ["直感", "共感", "やさしさ"],
     "love_keywords": ["夢みる心", "包み込む愛", "言葉にならない想い"],
     "love_style": "相手に寄り添う名人。尽くしすぎて自分を見失わないことが鍵です。",
     "color": "ラベンダー", "item": "やわらかな布／音楽", "place": "海辺・映画館"},
]

BY_EN = {s["en"]: s for s in ZODIAC_SIGNS}

ELEMENT_COLORS = {
    "火": {"bg_start": (190, 60, 40), "bg_end": (80, 14, 16)},
    "地": {"bg_start": (70, 110, 55), "bg_end": (22, 48, 22)},
    "風": {"bg_start": (48, 120, 180), "bg_end": (16, 48, 96)},
    "水": {"bg_start": (60, 70, 170), "bg_end": (18, 24, 86)},
}
ELEMENT_ACCENT = {"火": (255, 198, 120), "地": (205, 245, 160), "風": (198, 232, 255), "水": (196, 206, 255)}

# 西洋の4元素と五行の対応（暦の計算と重ねるため）
ELEMENT_TO_GOGYO = {"火": "火", "地": "土", "風": "木", "水": "水"}

COMPLEMENT = {"火": "風", "風": "火", "地": "水", "水": "地"}

# 恋愛が主軸だが、回ごとに暮らしのテーマを1つ添える（仕事の悩みなど）
SUB_THEMES = [
    {"key": "work", "label": "仕事・職場の人間関係",
     "lead": "職場での立ち位置や、気を使う相手との距離の取り方", "advice_focus": "働き方と、職場での人との距離"},
    {"key": "friend", "label": "友人・人づきあい",
     "lead": "友人との距離感や、誘いを断れないときの心の置きどころ", "advice_focus": "友人関係の整理と、断る勇気"},
    {"key": "money", "label": "お金の使い方",
     "lead": "自分のために使うお金と、人のために使うお金のバランス", "advice_focus": "お金の使い方と、心の余裕"},
    {"key": "self", "label": "心と体の整え方",
     "lead": "疲れのたまり方や、休むことへの罪悪感", "advice_focus": "休み方と、自分への声のかけ方"},
    {"key": "family", "label": "家族との関係",
     "lead": "家族に言えずにいること、言いすぎてしまうこと", "advice_focus": "家族との間合いと、言葉の選び方"},
]


def sub_theme_for(period_start) -> dict:
    """期間ごとに暮らしのテーマを順番に選ぶ（週がずれても同じ週なら同じテーマ）"""
    return SUB_THEMES[period_start.isocalendar()[1] % len(SUB_THEMES)]


def compat_score(a: dict, b: dict) -> int:
    """恋愛の相性スコア（0〜5）。同じ元素と補い合う元素を高く、区分（活動・不動・柔軟）の重なりを低く見る"""
    score = 1
    if a["element"] == b["element"]:
        score += 3
    elif COMPLEMENT[a["element"]] == b["element"]:
        score += 3
    elif a["element"] in ("火", "地") and b["element"] in ("火", "地"):
        score += 1
    elif a["element"] in ("風", "水") and b["element"] in ("風", "水"):
        score += 1
    if a["modality"] != b["modality"]:
        score += 1
    return min(score, 5)


def compat_comment(a: dict, b: dict) -> str:
    if a["element"] == b["element"]:
        return f"同じ{a['element']}のエレメント同士。言葉にしなくても伝わる、安心感のある関係です。"
    if COMPLEMENT[a["element"]] == b["element"]:
        return f"{a['element']}と{b['element']}は、互いの足りないところを自然に補い合う組み合わせです。"
    if a["modality"] == b["modality"]:
        return "進み方のペースが似ているぶん、ぶつかることもありますが、本音で向き合える相手です。"
    return "価値観の違いが刺激になる相手。歩み寄るほど、思いがけない深さが生まれます。"
