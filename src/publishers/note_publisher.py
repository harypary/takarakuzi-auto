"""note.com 自動投稿（Playwright ブラウザ自動化）

12.uranai の NotePublisher を移植。ハッシュタグ上限のみ10個に拡張。
"""

import base64
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.config import OUTPUT_DIR
from src.publishers import session_store
from src.utils.logger import get_logger

logger = get_logger("note_publisher")

NOTE_BASE_URL = "https://note.com"
NOTE_NEW_ARTICLE_URL = f"{NOTE_BASE_URL}/notes/new"
SESSION_FILE = OUTPUT_DIR / "note_session.json"
MAX_HASHTAGS = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _wait(seconds: float):
    time.sleep(seconds + random.uniform(0, 0.5))


def _paid_anchor(teaser: str, paid: str) -> str:
    """有料部分の先頭を見分けるための、無料部分に含まれない最初の行"""
    for line in paid.splitlines():
        line = line.strip()
        if line and not re.fullmatch(r"[━─=\-\s]+", line) and line not in teaser:
            return line
    raise ValueError("有料部分の先頭行を特定できません")


def is_logged_in(context) -> bool:
    resp = context.request.get(f"{NOTE_BASE_URL}/api/v2/current_user")
    if resp.status != 200:
        return False
    try:
        return bool(resp.json().get("data"))
    except Exception:
        return False


def login(page: Page, email: str, password: str) -> None:
    """メールアドレスとパスワードで note にログインする"""
    page.goto(f"{NOTE_BASE_URL}/login", wait_until="networkidle", timeout=60000)
    _wait(2)
    page.fill('input[name="login"], input[autocomplete="username"], input[type="email"]', email)
    _wait(0.5)
    page.fill('input[name="password"], input[type="password"]', password)
    _wait(0.5)
    # 「Googleでログイン」等を誤って押さないよう、文言が完全一致のボタンだけを押す
    page.get_by_role("button", name="ログイン", exact=True).click(timeout=10000)
    for _ in range(20):
        _wait(1)
        if is_logged_in(page.context):
            return
    raise RuntimeError("note への自動ログインに失敗しました（画面構成の変更や追加認証の可能性があります）")


class NotePublisher:
    """note.com への有料記事自動投稿（セッション方式）"""

    def publish_article(
        self,
        title: str,
        teaser_content: str,
        paid_content: str,
        price: int,
        cover_image_path: Optional[str] = None,
        hashtags: Optional[list] = None,
    ) -> str:
        storage_state = self._load_session()
        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
            )
            context: BrowserContext = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                permissions=["clipboard-read", "clipboard-write"],
                storage_state=storage_state,
            )
            page: Page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.on("dialog", lambda dialog: dialog.accept())
            try:
                self._verify_session(page)
                return self._create_paid_article(
                    page, title, teaser_content, paid_content, price, cover_image_path, hashtags or []
                )
            except Exception:
                shot = OUTPUT_DIR / "logs" / f"publish_error_{int(time.time())}.png"
                try:
                    page.screenshot(path=str(shot), full_page=True)
                    logger.error(f"投稿失敗時のスクリーンショット: {shot}")
                except Exception:
                    pass
                raise
            finally:
                browser.close()

    def _load_session(self) -> dict:
        state = session_store.load_encrypted()
        if state:
            logger.info("リポジトリの暗号化セッションを読み込みました")
            return state
        session_b64 = os.environ.get("NOTE_SESSION_B64")
        if session_b64:
            logger.info("環境変数からセッションを読み込みました")
            return json.loads(base64.b64decode(session_b64).decode("utf-8"))
        if not SESSION_FILE.exists():
            raise FileNotFoundError(
                f"セッションファイルが見つかりません: {SESSION_FILE}\n"
                "先に python scripts/setup_note_session.py を実行してください"
            )
        logger.info(f"セッション読み込み: {SESSION_FILE}")
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    def _verify_session(self, page: Page):
        """ログイン状態を確認し、切れていればメールアドレスで再ログインして暗号化保存する"""
        if is_logged_in(page.context):
            logger.info("セッション有効 - ログイン済み")
            return
        email, password = os.environ.get("NOTE_EMAIL"), os.environ.get("NOTE_PASSWORD")
        if not (email and password):
            raise RuntimeError(
                "note のセッションが切れています。NOTE_EMAIL / NOTE_PASSWORD を設定するか、"
                "setup_note_session.py を再実行してください"
            )
        logger.warning("セッションが切れているため、メールアドレスで再ログインします")
        login(page, email, password)
        if session_store.save_encrypted(page.context.storage_state()):
            logger.info("新しいセッションを暗号化して保存しました")

    def _create_paid_article(self, page, title, teaser, paid, price, cover_image_path, hashtags) -> str:
        logger.info(f"記事作成開始: {title}")
        page.goto(NOTE_NEW_ARTICLE_URL, wait_until="networkidle")
        _wait(3)

        self._fill_title(page, title)
        _wait(1)

        if cover_image_path and Path(cover_image_path).exists():
            self._upload_cover(page, cover_image_path)
            _wait(3)

        anchor = self._fill_body(page, teaser, paid)
        _wait(2)

        page.click('button:has-text("公開に進む")', timeout=8000)
        _wait(4)

        if hashtags:
            self._set_hashtags(page, hashtags)
            _wait(1)

        self._set_price(page, price)
        _wait(1)

        page.click('button:has-text("有料エリア設定")', timeout=8000)
        _wait(4)

        page.click('button:has-text("投稿する")', timeout=8000)
        _wait(8)

        return self._verify_published(page, anchor)

    def _verify_published(self, page: Page, anchor: str) -> str:
        """公開後に API で状態と有料エリアの位置を確認し、公開URLを返す"""
        match = re.search(r"notes/(n[0-9a-z]+)", page.url)
        if not match:
            raise RuntimeError(f"投稿後のURLから記事IDを取得できません: {page.url}")
        key = match.group(1)
        data = page.request.get(f"{NOTE_BASE_URL}/api/v3/notes/{key}").json().get("data") or {}
        public_url = f"{NOTE_BASE_URL}/{(data.get('user') or {}).get('urlname')}/n/{key}"
        if data.get("status") != "published":
            raise RuntimeError(f"記事が公開状態になっていません（status={data.get('status')}）: {public_url}")
        body, separator = data.get("body") or "", data.get("separator") or ""
        cut = body.find(separator) if separator else -1
        if cut < 0 or anchor in re.sub(r"<[^>]+>", "", body[:cut]):
            raise RuntimeError(f"公開後の確認で有料部分が無料側に含まれています。すぐに記事を非公開にしてください: {public_url}")
        logger.info(f"投稿完了（有料エリアの位置を確認済み）: {public_url}")
        return public_url

    def _fill_title(self, page: Page, title: str):
        for sel in ('textarea[placeholder*="タイトル"]', 'input[placeholder*="タイトル"]', '[data-placeholder*="タイトル"]'):
            try:
                page.wait_for_selector(sel, timeout=5000)
                page.fill(sel, title)
                return
            except Exception:
                continue
        logger.warning("タイトル入力欄が見つかりません。キーボード入力を試みます")
        page.keyboard.press("Tab")
        page.keyboard.type(title)

    def _upload_cover(self, page: Page, image_path: str):
        try:
            file_inputs = page.query_selector_all('input[type="file"]')
            if file_inputs:
                file_inputs[0].set_input_files(image_path)
                return
            # 新エディタ：「画像を追加」→ メニューの「画像をアップロード」→ ファイル選択
            #            → 「画像のサイズの変更」ダイアログで「保存」
            add_button = page.locator('button:has([aria-label="画像を追加"])').first
            if not add_button.count():
                logger.warning("カバー画像の追加ボタンが見つかりません（画像なしで続行）")
                return
            add_button.click(force=True, timeout=5000)
            _wait(1)
            with page.expect_file_chooser(timeout=8000) as chooser:
                page.locator('button:has-text("画像をアップロード")').first.click(timeout=5000)
            chooser.value.set_files(image_path)
            _wait(3)
            page.locator('[role="dialog"] button:has-text("保存")').first.click(timeout=8000)
            try:
                page.wait_for_selector('img[src*="/uploads/images/"]', state="attached", timeout=15000)
                logger.info("カバー画像を設定しました")
            except Exception:
                logger.warning("カバー画像のアップロード完了を確認できませんでした（続行）")
        except Exception as e:
            logger.warning(f"カバー画像アップロード失敗（スキップ）: {e}")

    def _fill_body(self, page: Page, teaser: str, paid: str):
        body_el = None
        for sel in (".ProseMirror", '[role="textbox"]', '[contenteditable="true"]'):
            try:
                page.wait_for_selector(sel, timeout=5000)
                body_el = page.query_selector(sel)
                if body_el:
                    break
            except Exception:
                continue
        if body_el:
            body_el.click()
        else:
            logger.warning("本文エリアが見つかりません")
        _wait(0.5)

        # 無料部分と有料部分をまとめて貼り付けてから、境界に有料エリア線を入れる。
        # 線を先に入れるとカーソルが線の手前に残り、有料部分が無料側に入ってしまう。
        anchor = _paid_anchor(teaser, paid)
        self._paste(page, f"{teaser}\n\n{paid}")
        _wait(2)
        self._insert_paid_boundary(page, anchor)
        return anchor

    def _paste(self, page: Page, text: str):
        """本文エディタに貼り付ける。

        ヘッドレス環境ではクリップボードAPIがフォーカス不足で拒否されるため、
        DataTransfer 付きの paste イベントを直接エディタに送る（ProseMirror が処理する）。
        """
        pasted = page.evaluate(
            """(text) => {
                const el = document.querySelector('.ProseMirror') || document.querySelector('[contenteditable="true"]');
                if (!el) return false;
                el.focus();
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                const ev = new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true});
                el.dispatchEvent(ev);
                return ev.defaultPrevented;
            }""",
            text,
        )
        if pasted:
            return
        logger.warning("paste イベントが処理されなかったため、クリップボード経由で貼り付けます")
        page.bring_to_front()
        page.evaluate(f"navigator.clipboard.writeText({json.dumps(text)})")
        _wait(0.3)
        page.keyboard.press("Control+v")

    def _insert_paid_boundary(self, page: Page, anchor: str):
        """無料部分の最後のブロックをクリック → 「メニューを開く」(+) → 「有料エリア指定」。
        線はクリックしたブロックの直後に入る。入れた後、位置が正しいかを検証する。"""
        index = page.evaluate(
            """(anchor) => {
                const blocks = [...document.querySelectorAll('.ProseMirror > *')];
                let i = blocks.findIndex(b => (b.innerText || '').includes(anchor));
                if (i <= 0) return -1;
                while (i > 1 && /^[━─\\s]*$/.test(blocks[i - 1].innerText || '')) i--;
                return i - 1;
            }""",
            anchor,
        )
        if index < 0:
            raise RuntimeError("有料部分の先頭が本文中に見つかりません")
        last_free = page.locator(".ProseMirror > *").nth(index)
        last_free.click()
        _wait(0.3)
        last_free.hover()
        _wait(0.5)
        page.click('[aria-label="メニューを開く"]', timeout=5000)
        _wait(0.5)
        page.click("text=有料エリア指定", timeout=5000)
        _wait(1.5)

        result = page.evaluate(
            """(anchor) => {
                const lines = document.querySelectorAll('.ProseMirror > paywall-line');
                if (lines.length !== 1) return 'paywall-line が' + lines.length + '個';
                let next = lines[0].nextElementSibling;
                while (next && /^[━─\\s]*$/.test(next.innerText || '')) next = next.nextElementSibling;
                if (!next || !(next.innerText || '').includes(anchor)) return '線の直後が有料部分の先頭ではありません';
                return 'ok';
            }""",
            anchor,
        )
        if result != "ok":
            raise RuntimeError(f"有料エリア線の位置が想定と違うため投稿を中止します（{result}）")
        logger.info("有料エリア線の位置を確認しました")

    def _set_price(self, page: Page, price: int):
        if page.get_by_text("本人情報の登録").first.is_visible():
            raise RuntimeError(
                "note の本人情報（氏名・住所）が未登録のため有料記事を設定できません。"
                "ブラウザで note にログインし、本人情報を登録してから再実行してください。"
            )
        loc = page.locator("#price").first
        if not loc.is_visible():
            # 記事タイプで「有料」を選ぶと価格欄が出る画面構成に対応
            try:
                page.get_by_text("有料", exact=True).first.click(timeout=3000)
                _wait(1)
            except Exception:
                pass
        loc.wait_for(state="visible", timeout=8000)
        loc.click(click_count=3)
        _wait(0.3)
        loc.fill(str(price))
        _wait(0.5)
        loc.press("Tab")
        logger.info(f"価格設定: {price}円")

    def _set_hashtags(self, page: Page, hashtags: list):
        try:
            loc = page.locator('input[placeholder*="ハッシュタグ"]').first
            loc.wait_for(state="visible", timeout=5000)
            for tag in hashtags[:MAX_HASHTAGS]:
                loc.fill(tag)
                loc.press("Enter")
                _wait(0.3)
        except Exception as e:
            logger.warning(f"ハッシュタグ設定失敗: {e}")
