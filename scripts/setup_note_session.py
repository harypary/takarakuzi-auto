"""note.com セッション初期化（初回のみ・手動ログイン）

PowerShell などから実行してください:

  cd C:\\Users\\haryp\\game\\31.takarakuzi
  python scripts/setup_note_session.py

ブラウザが開くので、宝くじ用の note アカウントでログインし、ターミナルで Enter を押します。
ログインできているかを確認してから保存します（未ログインなら保存せずにやり直せます）。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.publishers.note_publisher import SESSION_FILE


def _current_user(context):
    """ログイン中ならユーザー情報、未ログインなら None"""
    resp = context.request.get("https://note.com/api/v2/current_user")
    if resp.status != 200:
        return None
    try:
        return resp.json().get("data") or None
    except Exception:
        return None


def main():
    from playwright.sync_api import sync_playwright

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto("https://note.com/login")
        print("開いたブラウザで、宝くじ用の note アカウントにログインしてください。")
        print("ログイン後、note のトップページなどが表示されたのを確認してから Enter を押してください。")

        while True:
            answer = input("ログイン完了後、Enter キーを押してください（中止は q）>>> ")
            if answer.strip().lower() == "q":
                print("中止しました。セッションは保存していません。")
                browser.close()
                return
            user = _current_user(context)
            if user:
                break
            print("まだログインが確認できません。ブラウザでログインを完了してから、もう一度 Enter を押してください。")

        state = context.storage_state()
        SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"ログイン確認OK: {user.get('nickname')}（note.com/{user.get('urlname')}）")
        print(f"セッション保存完了: {SESSION_FILE}（Cookie {len(state.get('cookies', []))}件）")
        browser.close()


if __name__ == "__main__":
    main()
