"""note.com セッション自動更新（GitHub Actions から毎月実行）

1. NOTE_EMAIL / NOTE_PASSWORD で自動ログインし、セッションを保存
2. GITHUB_PAT と GITHUB_REPO があれば Secret NOTE_SESSION_B64 を更新

12.uranai 版からの変更: PAT を GITHUB_PAT（旧名 GH_PAT も可）から読むよう修正。
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.publishers.note_publisher import SESSION_FILE

NOTE_EMAIL = os.getenv("NOTE_EMAIL", "")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD", "")
GITHUB_PAT = os.getenv("GITHUB_PAT") or os.getenv("GH_PAT", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")


def login_and_save_session() -> None:
    from playwright.sync_api import sync_playwright

    print("[1/3] note.com に自動ログイン中...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.goto("https://note.com/login", wait_until="networkidle")
        time.sleep(2)
        page.fill('input[name="email"], input[type="email"]', NOTE_EMAIL)
        time.sleep(0.5)
        page.fill('input[name="password"], input[type="password"]', NOTE_PASSWORD)
        time.sleep(0.5)
        page.click('button[type="submit"], button:has-text("ログイン")')
        time.sleep(4)
        if "login" in page.url:
            raise RuntimeError(f"ログイン失敗: {page.url}")

        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(context.storage_state(), ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()
    print(f"    セッション保存完了: {SESSION_FILE}")


def update_github_secret(secret_value: str) -> None:
    if not GITHUB_PAT or not GITHUB_REPO:
        print("[3/3] GITHUB_PAT / GITHUB_REPO が未設定のためスキップ")
        return

    print(f"[3/3] GitHub Secret 更新中: {GITHUB_REPO} / NOTE_SESSION_B64")
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key", headers=headers)
    with urllib.request.urlopen(req) as resp:
        pk = json.loads(resp.read())

    from nacl import public as nacl_public

    box = nacl_public.SealedBox(nacl_public.PublicKey(base64.b64decode(pk["key"])))
    encrypted = base64.b64encode(box.encrypt(secret_value.encode())).decode()

    body = json.dumps({"encrypted_value": encrypted, "key_id": pk["key_id"]}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/NOTE_SESSION_B64",
        data=body, headers=headers, method="PUT",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API エラー: {e.code} {e.read().decode()}")
    if status not in (201, 204):
        raise RuntimeError(f"GitHub API 予期しないステータス: {status}")
    print("    NOTE_SESSION_B64 更新成功")


def main():
    if not NOTE_EMAIL or not NOTE_PASSWORD:
        print("ERROR: NOTE_EMAIL / NOTE_PASSWORD が設定されていません")
        sys.exit(1)
    login_and_save_session()
    b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()
    print(f"[2/3] Base64 エンコード完了（{len(b64)}文字）")
    update_github_secret(b64)


if __name__ == "__main__":
    main()
