"""学習状態・予想記録の保存"""

import json

from src.config import PREDICTIONS_DIR, STATE_DIR


def _read(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_state(game_key: str) -> dict:
    return _read(STATE_DIR / f"{game_key}.json", {"weeks": {}})


def save_state(game_key: str, state: dict) -> None:
    _write(STATE_DIR / f"{game_key}.json", state)


def load_prediction(game_key: str, draw: int):
    return _read(PREDICTIONS_DIR / game_key / f"{draw:05d}.json", None)


def save_prediction(game_key: str, draw: int, data: dict) -> None:
    _write(PREDICTIONS_DIR / game_key / f"{draw:05d}.json", data)
