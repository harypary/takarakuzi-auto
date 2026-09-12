"""note.com 自動投稿（Playwright ブラウザ自動化）

12.uranai の NotePublisher を移植。ハッシュタグ上限のみ10個に拡張。
"""

import base64
import json
import os
import random
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.config import OUTPUT_DIR
from src.utils.logger import get_logger

logger = get_logger("note_publisher")

NOTE_BASE_URL = "https://note.com"
NOTE_NEW_ARTICLE_URL = f"{NOTE_BASE_URL}/notes/new"
SESSION_FILE = OUTPUT_DIR / "note_session.json"
MAX_HASHTAGS = 10


def _wait(seconds: float):
    time.sleep(seconds + random.uniform(0, 0.5))


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
        page.goto(NOTE_BASE_URL, wait_until="networkidle", timeout=30000)
        _wait(2)
        if page.query_selector('[data-testid="user-icon"], .o-header__userIcon, a[href*="/settings"]'):
            logger.info("セッション有効 - ログイン済み")
        else:
            logger.warning("ログイン状態を確認できません。失敗する場合は setup_note_session.py を再実行してください")

    def _create_paid_article(self, page, title, teaser, paid, price, cover_image_path, hashtags) -> str:
        logger.info(f"記事作成開始: {title}")
        page.goto(NOTE_NEW_ARTICLE_URL, wait_until="networkidle")
        _wait(3)

        self._fill_title(page, title)
        _wait(1)

        if cover_image_path and Path(cover_image_path).exists():
            self._upload_cover(page, cover_image_path)
            _wait(3)

        self._fill_body(page, teaser, paid)
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

        url = page.url
        logger.info(f"投稿完了: {url}")
        return url

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
            else:
                logger.warning("カバー画像の入力欄が見つかりません")
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

        self._paste(page, teaser)
        _wait(0.5)

        self._insert_paid_boundary(page)
        _wait(1)

        self._paste(page, paid)
        _wait(2)

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

    def _insert_paid_boundary(self, page: Page):
        """本文の「メニューを開く」(+) → 「有料エリア指定」で区切り線を入れる"""
        page.keyboard.press("Control+End")
        _wait(0.5)
        page.hover(".ProseMirror > *:last-child", timeout=5000)
        _wait(0.4)
        page.click('[aria-label="メニューを開く"]', timeout=5000)
        _wait(0.5)
        page.click("text=有料エリア指定", timeout=5000)
        _wait(1.0)

    def _set_price(self, page: Page, price: int):
        loc = page.locator("#price").first
        loc.wait_for(state="visible", timeout=5000)
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
