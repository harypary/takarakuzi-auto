"""note加盟店規約（誤解を招く表現・景品表示法・購入を煽る行為の禁止）への対応"""

import re

DISCLAIMER = (
    "【ご注意】\n"
    "本記事は、過去の当せん番号の統計的な整理と、暦（六曜・九星・干支・数秘）の考え方を組み合わせた"
    "「数字選びの参考情報」です。宝くじの抽せんは毎回独立した無作為のもので、どのような分析でも"
    "当せん確率そのものを高めることはできず、当せんを保証するものではありません。"
    "購入はご自身の判断で、生活に支障のない範囲でお楽しみください。"
)

NG_PATTERNS = [
    r"必ず当", r"絶対に?当", r"確実に?当", r"当せん保証", r"当選保証", r"保証します", r"保証付",
    r"必勝", r"儲か", r"稼げ", r"億り人", r"激熱", r"神予想", r"100\s*[%％]\s*(当|的中|勝|儲)", r"的中率\s*\d",
    r"当たります", r"当たる予想", r"勝てる", r"高確率で当", r"負けない",
]


def find_ng(text: str) -> list:
    return [m.group(0) for p in NG_PATTERNS for m in re.finditer(p, text)]


def assert_clean(*texts: str) -> None:
    hits = sorted({h for t in texts for h in find_ng(t)})
    if hits:
        raise ValueError(f"規約上のNG表現を検出したため投稿を中止します: {hits}")
