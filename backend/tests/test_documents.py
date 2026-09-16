"""Tests for document upload, listing, and deletion."""

import asyncio
import io
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from models.database import Document
from services import document_service
from utils.security import validate_file_type


def _txt_file(content: str = "Hello, this is a test document about refund policies."):
    return {"file": ("notes.txt", io.BytesIO(content.encode()), "text/plain")}


def test_upload_rejects_unsupported_file_type(client, auth_headers):
    files = {"file": ("image.png", io.BytesIO(b"\x89PNG\r\n"), "image/png")}
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert resp.status_code == 415


def test_upload_requires_auth(client):
    resp = client.post("/api/v1/documents/upload", files=_txt_file())
    assert resp.status_code == 401


def test_upload_txt_processes_synchronously_in_tests(client, auth_headers, mock_embeddings):
    """Celery runs in eager mode during tests, so by the time upload
    returns, the background pipeline has already run against the mocked
    embedding call."""
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file())

    assert resp.status_code == 202
    doc_id = resp.json()["id"]

    detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"
    assert detail.json()["chunk_count"] >= 1


def test_list_documents_only_returns_own_documents(client, auth_headers, mock_embeddings):
    client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file())

    other_user = {
        "email": "other@acme-test.com",
        "full_name": "Other Person",
        "password": "another-pass-1",
    }
    client.post("/api/v1/auth/register", json=other_user)
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other_user["email"], "password": other_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    mine = client.get("/api/v1/documents", headers=auth_headers)
    theirs = client.get("/api/v1/documents", headers=other_headers)

    assert mine.json()["total"] == 1
    assert theirs.json()["total"] == 0


def test_cannot_access_another_users_document(client, auth_headers, mock_embeddings):
    upload = client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file())
    doc_id = upload.json()["id"]

    other_user = {
        "email": "intruder@acme-test.com",
        "full_name": "Intruder",
        "password": "sneaky-pass-1",
    }
    client.post("/api/v1/auth/register", json=other_user)
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other_user["email"], "password": other_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    resp = client.get(f"/api/v1/documents/{doc_id}", headers=other_headers)
    assert resp.status_code == 404


def test_delete_document_removes_it(client, auth_headers, mock_embeddings):
    upload = client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file())
    doc_id = upload.json()["id"]

    delete_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_upload_empty_text_file_marks_document_failed(client, auth_headers, mock_embeddings):
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file("   "))
    doc_id = resp.json()["id"]

    detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert detail.json()["status"] == "failed"


def test_upload_rejects_fake_docx_declared_as_docx(client, auth_headers):
    files = {
        "file": (
            "fake.docx",
            io.BytesIO(b"this is not a zip-based docx document"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert resp.status_code == 415


def test_upload_rejects_binary_declared_as_text(client, auth_headers):
    files = {"file": ("fake.txt", io.BytesIO(b"\xff\xfe\x00\x01"), "text/plain")}
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert resp.status_code == 415


@pytest.mark.parametrize("content,valid", [
    (b"a" * 65535 + "é".encode(), True),
    (b"a" * 65536 + b"\xff", False),
])
def test_text_validation_checks_full_utf8_file(tmp_path, content, valid):
    path = tmp_path / "input.txt"
    path.write_bytes(content)
    assert validate_file_type(path, "txt") is valid


@pytest.mark.parametrize("failure", ["read", "commit"])
def test_failed_upload_removes_file_and_rolls_back(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(document_service, "UPLOAD_DIR", tmp_path)
    upload = UploadFile(io.BytesIO(b"valid text"), filename="notes.txt",
                        headers=Headers({"content-type": "text/plain"}))
    db = Mock()
    if failure == "read":
        upload.read = AsyncMock(side_effect=[b"partial", OSError("read failed")])
    else:
        db.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises((OSError, RuntimeError)):
        asyncio.run(document_service.save_upload(upload, "owner", db))
    assert list(tmp_path.iterdir()) == []
    if failure == "commit":
        db.rollback.assert_called_once()


def test_broker_failure_removes_pending_upload(client, auth_headers, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(document_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("api.routes.documents.process_document.delay",
                        Mock(side_effect=ConnectionError("broker unavailable")))
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=_txt_file())
    assert response.status_code == 503
    assert db_session.query(Document).count() == 0
    assert list(tmp_path.iterdir()) == []
