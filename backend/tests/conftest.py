"""Shared pytest fixtures.

Environment variables are set before any application module is imported,
because config.get_settings() is cached with @lru_cache — whichever values
are in os.environ the first time it's called are locked in for the whole
test process.
"""

import os
from pathlib import Path
from types import SimpleNamespace

TEST_ROOT = Path(__file__).parent / ".tmp"
TEST_ROOT.mkdir(exist_ok=True)

os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "pytest-only-secret-do-not-use-in-production-xxxxxxxxxx"
os.environ["OPENAI_API_KEY"] = "sk-test-placeholder"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["CHROMA_PERSIST_DIR"] = str(TEST_ROOT / "chroma")
os.environ["CHROMA_HOST"] = ""  # Tests use one process and an embedded store.
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"
os.environ["RATE_LIMIT_AUTH"] = "1000/minute"   # Don't let rate limiting interfere with test runs
os.environ["RATE_LIMIT_DEFAULT"] = "1000/minute"

import pytest
from fastapi.testclient import TestClient

from main import app
from models.database import Base, SessionLocal, engine
from worker.celery_app import celery_app

# Run Celery tasks synchronously and in-process — no broker required.
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)


def _ensure_tokenizer_available():
    """tiktoken downloads its BPE file from openaipublic.blob.core.windows.net
    on first use and caches it locally afterward (see the Dockerfile, which
    warms this cache at build time for exactly this reason). A network-
    restricted test runner that has never made that one-time download will
    fail here — fall back to a plain whitespace tokenizer so the suite can
    still verify chunking *logic* (boundaries, overlap, loop guards) even
    though token counts won't match tiktoken's real BPE counts in that case.
    """
    import re
    from unittest.mock import MagicMock

    import tiktoken

    try:
        tiktoken.get_encoding("cl100k_base")
        return
    except Exception:
        pass

    class _FallbackEncoding:
        def encode(self, text, **kwargs):
            return re.findall(r"\S+|\s+", text)

        def decode(self, tokens):
            return "".join(tokens)

    fallback = _FallbackEncoding()
    tiktoken.get_encoding = MagicMock(return_value=fallback)
    tiktoken.encoding_for_model = MagicMock(return_value=fallback)


_ensure_tokenizer_available()


@pytest.fixture(autouse=True)
def _reset_database():
    """Every test starts with an empty, freshly-created schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_payload():
    return {
        "email": "jordan@acme-test.com",
        "full_name": "Jordan Rivera",
        "password": "correct-horse-1",
        "company": "Acme Test Co",
    }


@pytest.fixture
def registered_user(client, user_payload):
    resp = client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def auth_headers(client, user_payload, registered_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_embeddings(monkeypatch):
    """Patch OpenAI embedding calls to return small, deterministic vectors
    instead of hitting the real API."""

    def _fake_create(model, input, **kwargs):
        texts = input if isinstance(input, list) else [input]
        data = [SimpleNamespace(embedding=[0.1] * 16, index=i) for i in range(len(texts))]
        return SimpleNamespace(data=data)

    monkeypatch.setattr("services.embedding_service.openai_client.embeddings.create", _fake_create)
    return _fake_create


@pytest.fixture
def fake_chat_responses(monkeypatch):
    """Returns a function that patches a chat.completions.create target to
    return a queued sequence of canned JSON/text responses, one per call —
    used for services that make multiple sequential model calls."""

    def _patch(target: str, contents: list, tokens: int = 42):
        responses = iter(contents)

        def _fake_create(*args, **kwargs):
            content = next(responses)
            message = SimpleNamespace(content=content)
            choice = SimpleNamespace(message=message)
            usage = SimpleNamespace(total_tokens=tokens)
            return SimpleNamespace(choices=[choice], usage=usage)

        monkeypatch.setattr(target, _fake_create)

    return _patch
