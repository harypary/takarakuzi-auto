from src.publishers import session_store


def test_encrypt_roundtrip(tmp_path):
    key = session_store.generate_key()
    path = tmp_path / "session.enc"
    state = {"cookies": [{"name": "a", "value": "secret-value"}], "origins": []}
    assert session_store.save_encrypted(state, key, path)
    assert b"secret-value" not in path.read_bytes()
    assert session_store.load_encrypted(key, path) == state


def test_without_key_does_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("SESSION_KEY", raising=False)
    path = tmp_path / "session.enc"
    assert session_store.save_encrypted({"cookies": []}, None, path) is False
    assert session_store.load_encrypted(None, path) is None
