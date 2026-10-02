"""年末ジャンボなど、次のジャンボ宝くじの日程が公式サイトに出たかを確認する

GitHub Actions（毎週）から実行し、見つかったら GitHub Issue を作って知らせる。
発表され次第 scripts/post_jumbo.py の JUMBO を差し替えれば、無料記事を出せる。
"""

import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import get_logger

logger = get_logger("check_jumbo")

PAGES = ["https://www.takarakuji-official.jp/kuji/jumbo/", "https://www.takarakuji-official.jp/brand/jumbo/"]
TARGET = "年末ジャンボ"
# 「発売期間 ◯月◯日〜」のように日付が併記されていれば発表済みとみなす
DATE_NEAR_TARGET = re.compile(rf"{TARGET}[^。]{{0,400}}?(\d{{1,2}})月(\d{{1,2}})日")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    return re.sub(r"<[^>]+>", " ", html)


def main():
    hits = []
    for url in PAGES:
        try:
            text = fetch(url)
        except Exception as e:
            logger.warning(f"取得失敗 {url}: {e}")
            continue
        for m in DATE_NEAR_TARGET.finditer(text):
            hits.append((url, re.sub(r"\s+", " ", m.group(0))[:160]))

    if not hits:
        logger.info(f"{TARGET} の日程はまだ公式サイトに出ていません")
        return

    body = "\n".join(f"- {snippet}\n  （{url}）" for url, snippet in hits[:6])
    logger.info(f"{TARGET} の日程らしい記載を見つけました:\n{body}")

    if os.environ.get("GITHUB_ACTIONS") and os.environ.get("GITHUB_TOKEN"):
        title = f"{TARGET} の日程が公式サイトに出ています"
        issue_body = (
            f"{TARGET} の日程らしい記載を見つけました。\n\n{body}\n\n"
            "公式サイトで発売期間・抽せん日・賞金を確認し、scripts/post_jumbo.py の JUMBO を差し替えて "
            "`python scripts/post_jumbo.py --dry-run` → 内容確認 → 投稿してください。"
        )
        subprocess.run(["gh", "issue", "create", "--title", title, "--body", issue_body], check=False)


if __name__ == "__main__":
    main()
