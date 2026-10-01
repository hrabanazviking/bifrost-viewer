"""Security tests and lifespans must never open the real user's credential state."""
import os

import pytest

os.environ.setdefault("VIEWER_DB_URL", "postgresql://nowhere/test")
os.environ.setdefault("VIEWER_TOKEN", "test-token")
os.environ.setdefault("VIEWER_OLLAMA_URL", "http://localhost:11434")
os.environ.setdefault("VIEWER_EMBED_MODEL", "nomic-embed-text")
os.environ.setdefault("VIEWER_CHAT_MODEL", "llama3.2:3b")


@pytest.fixture(autouse=True)
def private_security(monkeypatch, tmp_path):
    import viewer
    monkeypatch.setattr(viewer, "SECURITY_DIR", tmp_path / "security")
    monkeypatch.setattr(viewer, "_security_store", None)
    monkeypatch.setattr(viewer, "_ingest_queue", None)
    monkeypatch.setattr(viewer, "_chat_router", None)
    monkeypatch.delenv("VIEWER_CHAT_BACKEND", raising=False)
    monkeypatch.delenv("VIEWER_CHAT_API_KEY_FILE", raising=False)
    monkeypatch.delenv("VIEWER_CHAT_URL", raising=False)
    monkeypatch.delenv("VIEWER_CHAT_FALLBACK", raising=False)
    monkeypatch.delenv("VIEWER_API_INGEST_ENV_FILE", raising=False)
    yield
    if viewer._ingest_queue:
        viewer._ingest_queue.stop()
    if viewer._chat_router:
        viewer._chat_router.close()
