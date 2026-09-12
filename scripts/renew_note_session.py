"""note.com セッション自動更新（GitHub Actions から毎月実行）

NOTE_EMAIL / NOTE_PASSWORD で自動ログインし、新しいセッションを SESSION_KEY で暗号化して
data/session/note_session.enc に保存する。ワークフローがそれをコミットするので、
GitHub の Personal Access Token は不要（トークンの期限切れも起きない）。
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config import OUTPUT_DIR
from src.publishers import session_store
from src.publishers.note_publisher import NOTE_BASE_URL, SESSION_FILE, USER_AGENT, login


def main():
    email, password = os.getenv("NOTE_EMAIL", ""), os.getenv("NOTE_PASSWORD", "")
    if not email or not password:
        print("ERROR: NOTE_EMAIL / NOTE_PASSWORD が設定されていません")
        sys.exit(1)
    if not os.getenv("SESSION_KEY"):
        print("ERROR: SESSION_KEY が設定されていません")
        sys.exit(1)

    from playwright.sync_api import sync_playwright

    print("[1/2] note.com に自動ログイン中...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900}, user_agent=USER_AGENT)
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        try:
            login(page, email, password)
        except Exception:
            shot = OUTPUT_DIR / "logs" / "renew_error.png"
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True)
            print(f"ログイン失敗時のスクリーンショット: {shot}")
            raise
        user = context.request.get(f"{NOTE_BASE_URL}/api/v2/current_user").json().get("data") or {}
        state = context.storage_state()
        browser.close()

    print(f"    ログイン確認OK: {user.get('nickname')}（note.com/{user.get('urlname')}）")
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    session_store.save_encrypted(state)
    print(f"[2/2] 暗号化セッションを保存: {session_store.ENCRYPTED_FILE}")


if __name__ == "__main__":
    main()
