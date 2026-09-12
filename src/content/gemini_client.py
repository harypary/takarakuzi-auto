"""Gemini API ラッパー（JSON出力・リトライ込み）"""

import json
import os
import time

from src.utils.logger import get_logger

logger = get_logger("gemini_client")


class GeminiClient:
    MODEL = "gemini-2.5-flash"
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 10

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        from google import genai

        self._client = genai.Client(api_key=api_key)

    def generate_json(self, prompt: str, temperature: float = 0.7) -> dict:
        from google.genai import types

        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=temperature,
            response_mime_type="application/json",
        )
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.models.generate_content(model=self.MODEL, contents=prompt, config=config)
                return json.loads(response.text)
            except Exception as e:
                logger.warning(f"Gemini API エラー（{attempt + 1}/{self.MAX_RETRIES}）: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_BASE_DELAY * (attempt + 1))
        raise RuntimeError("Gemini API の呼び出しに失敗しました")
