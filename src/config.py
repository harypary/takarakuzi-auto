"""ゲーム定義・シリーズ（記事）定義・共通設定"""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = DATA_DIR / "results"
STATE_DIR = DATA_DIR / "state"
PREDICTIONS_DIR = DATA_DIR / "predictions"
OUTPUT_DIR = ROOT / "output"

# ブランド（アカウント名・モデル名はここだけ変えれば全記事に反映される）
BRAND = "暦×統計の数字研究ノート"
MODEL_NAME = "KOYOMI-STAT"

# 分析軸（特徴量）
FEATURES = ("hot", "trend", "cold", "carry", "slide", "koyomi")
FEATURE_LABELS = {
    "hot": "ホット（直近の出現頻度）",
    "trend": "トレンド（直近の上昇度）",
    "cold": "コールド（未出現期間）",
    "carry": "引っ張り（前回と同じ数字）",
    "slide": "スライド（前回の隣の数字）",
    "koyomi": "暦（九星・干支・数秘）",
}
FEATURE_SHORT = {
    "hot": "ホット",
    "trend": "トレンド",
    "cold": "コールド",
    "carry": "引っ張り",
    "slide": "スライド",
    "koyomi": "暦",
}
DEFAULT_WEIGHTS = {"hot": 0.22, "trend": 0.14, "cold": 0.20, "carry": 0.10, "slide": 0.12, "koyomi": 0.22}

# 予想の内訳（本命・対抗・穴）
PICK_TIERS = (("本命", 4), ("対抗", 3), ("穴", 3))
TIER_DESC = {
    "本命": "今週の重みで計算した総合スコア上位",
    "対抗": "暦の比重を2倍にして計算した上位",
    "穴": "コールド（未出現期間）の比重を2倍にして計算した上位",
}

WEEKDAY_JA = "月火水木金土日"
# 年末年始は抽せんが無い
NO_DRAW_MMDD = {(12, 31), (1, 1), (1, 2), (1, 3)}


@dataclass(frozen=True)
class Game:
    key: str
    name: str
    kind: str  # "loto" / "numbers"
    draw_weekdays: tuple  # 0=月
    sources: tuple
    max_number: int = 0
    pick: int = 0
    bonus: int = 0
    digits: int = 0


GAMES = {
    "loto6": Game(
        "loto6", "ロト6", "loto", (0, 3),
        ("https://loto6.thekyo.jp/data/loto6.csv", "https://loto-life.net/csv/loto6"),
        max_number=43, pick=6, bonus=1,
    ),
    "loto7": Game(
        "loto7", "ロト7", "loto", (4,),
        ("https://loto7.thekyo.jp/data/loto7.csv", "https://loto-life.net/csv/loto7"),
        max_number=37, pick=7, bonus=2,
    ),
    "miniloto": Game(
        "miniloto", "ミニロト", "loto", (1,),
        ("https://miniloto.thekyo.jp/data/miniloto.csv", "https://loto-life.net/csv/mini"),
        max_number=31, pick=5, bonus=1,
    ),
    "numbers3": Game(
        "numbers3", "ナンバーズ3", "numbers", (0, 1, 2, 3, 4),
        ("https://loto-life.net/csv/numbers3", "https://www.mk-mode.com/rails/loto/NUMBERS3_ALL.csv"),
        digits=3,
    ),
    "numbers4": Game(
        "numbers4", "ナンバーズ4", "numbers", (0, 1, 2, 3, 4),
        ("https://loto-life.net/csv/numbers4", "https://www.mk-mode.com/rails/loto/NUMBERS4_ALL.csv"),
        digits=4,
    ),
}


@dataclass(frozen=True)
class Series:
    key: str
    title_name: str
    games: tuple
    price: int
    hashtags: tuple
    color: tuple  # (背景上, 背景下, アクセント)


SERIES = {
    "numbers": Series(
        "numbers", "ナンバーズ3・4", ("numbers4", "numbers3"), 300,
        ("ナンバーズ", "ナンバーズ予想", "ナンバーズ4", "ナンバーズ3", "宝くじ",
         "宝くじ予想", "データ分析", "占い", "開運", "数字選択式宝くじ"),
        ((18, 58, 120), (6, 18, 48), (120, 220, 255)),
    ),
    "loto6": Series(
        "loto6", "ロト6", ("loto6",), 400,
        ("ロト6", "ロト6予想", "ロト予想", "宝くじ", "宝くじ予想",
         "データ分析", "占い", "開運", "数字選択式宝くじ", "統計"),
        ((150, 24, 44), (48, 6, 16), (255, 205, 120)),
    ),
    "loto7": Series(
        "loto7", "ロト7", ("loto7",), 500,
        ("ロト7", "ロト7予想", "ロト予想", "宝くじ", "宝くじ予想",
         "データ分析", "占い", "開運", "数字選択式宝くじ", "キャリーオーバー"),
        ((92, 32, 142), (26, 8, 52), (232, 192, 255)),
    ),
}
