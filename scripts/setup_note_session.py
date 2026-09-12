"""note.com セッション初期化・再ログイン（手動）

PowerShell などから実行してください:

  cd C:\\Users\\haryp\\game\\31.takarakuzi
  python scripts/setup_note_session.py

ブラウザが開くので、宝くじ用の note アカウントでログインし、ターミナルで Enter を押します。
ログインできているかを確認してから保存します。続けて GitHub（自動投稿）への反映も行えます：
新しい暗号化キーを Secret SESSION_KEY に登録し、暗号化したセッションを data/session/ にコミットして push します。
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.publishers import session_store
from src.publishers.note_publisher import SESSION_FILE, is_logged_in

REPO = "harypary/takarakuzi-auto"


def push_to_github(state: dict) -> None:
    key = session_store.generate_key()
    session_store.save_encrypted(state, key)
    path = str(session_store.ENCRYPTED_FILE)
    try:
        subprocess.run(["git", "add", path], check=True)
        subprocess.run(["git", "commit", "-m", "session: 手動ログインで更新"], check=True)
        subprocess.run(["git", "pull", "--rebase"], check=True)
        subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git への反映に失敗しました（{e}）。Secret は更新していません。")
        return
    result = subprocess.run(["gh", "secret", "set", "SESSION_KEY", "-R", REPO], input=key, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"ERROR: SESSION_KEY の登録に失敗しました: {result.stderr.strip()}")
        return
    print("GitHub（自動投稿）に新しいセッションを反映しました")


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
            if is_logged_in(context):
                break
            print("まだログインが確認できません。ブラウザでログインを完了してから、もう一度 Enter を押してください。")

        user = context.request.get("https://note.com/api/v2/current_user").json().get("data") or {}
        state = context.storage_state()
        browser.close()

    SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ログイン確認OK: {user.get('nickname')}（note.com/{user.get('urlname')}）")
    print(f"セッション保存完了: {SESSION_FILE}（Cookie {len(state.get('cookies', []))}件）")

    answer = input("GitHub（自動投稿）にもこのセッションを反映しますか？ [Y/n] >>> ")
    if answer.strip().lower() in ("", "y", "yes"):
        push_to_github(state)


if __name__ == "__main__":
    main()
