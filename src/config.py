"""共通設定（パスと曜日表記）

商品・価格・ブランド名は src/love_config.py にある。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

WEEKDAY_JA = "月火水木金土日"
