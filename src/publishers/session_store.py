"""note セッションをリポジトリ内に暗号化して保存・読み込みする

GitHub Actions の GITHUB_TOKEN では Secret を書き換えられないため、
更新したセッションは SESSION_KEY（Secret）で暗号化して data/session/ にコミットする。
これにより Personal Access Token が不要になり、トークンの有効期限切れも起きない。
"""

import base64
import json
import os

from nacl import secret, utils

from src.config import DATA_DIR

ENCRYPTED_FILE = DATA_DIR / "session" / "note_session.enc"


def generate_key() -> str:
    return base64.b64encode(utils.random(secret.SecretBox.KEY_SIZE)).decode()


def _box(key_b64=None):
    key_b64 = key_b64 or os.environ.get("SESSION_KEY")
    if not key_b64:
        return None
    return secret.SecretBox(base64.b64decode(key_b64))


def save_encrypted(state: dict, key_b64=None, path=ENCRYPTED_FILE) -> bool:
    box = _box(key_b64)
    if box is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64encode(box.encrypt(json.dumps(state).encode("utf-8"))))
    return True


def load_encrypted(key_b64=None, path=ENCRYPTED_FILE):
    box = _box(key_b64)
    if box is None or not path.exists():
        return None
    return json.loads(box.decrypt(base64.b64decode(path.read_bytes())).decode("utf-8"))
