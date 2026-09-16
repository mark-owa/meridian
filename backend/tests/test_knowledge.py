"""Tests for the RAG query endpoint and the analytics dashboard."""

import io


def test_query_with_empty_knowledge_base_returns_graceful_message(client, auth_headers, mock_embeddings):
    resp = client.post(
        "/api/v1/knowledge/query", headers=auth_headers, json={"query": "What is our refund policy?"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"] == []
    assert "couldn't find" in body["answer"].lower()
    history = client.get("/api/v1/knowledge/history", headers=auth_headers).json()
    assert len(history) == 1
    assert history[0]["answer"] == body["answer"]


def test_query_rejects_too_short_question(client, auth_headers):
    resp = client.post("/api/v1/knowledge/query", headers=auth_headers, json={"query": "hi"})
    assert resp.status_code == 422


def test_query_returns_cited_answer(client, auth_headers, mock_embeddings, fake_chat_responses):
    files = {
        "file": (
            "policy.txt",
            io.BytesIO(b"Refunds are accepted within 30 days of purchase with a receipt."),
            "text/plain",
        )
    }
    client.post("/api/v1/documents/upload", headers=auth_headers, files=files)

    fake_chat_responses(
        "services.rag_service.openai_client.chat.completions.create",
        ["Refunds are accepted within 30 days of purchase, provided you have a receipt (Chunk 1)."],
    )

    resp = client.post(
        "/api/v1/knowledge/query",
        headers=auth_headers,
        json={"query": "What is our refund policy?"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sources"]) >= 1
    assert body["sources"][0]["document_name"] == "policy.txt"


def test_dashboard_stats_reflect_created_records(client, auth_headers):
    client.post(
        "/api/v1/leads",
        headers=auth_headers,
        json={
            "company_name": "Test Co",
            "contact_name": "Alex",
            "contact_email": "alex@test-co.com",
        },
    )

    resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_leads"] == 1
    assert body["qualified_leads"] == 0
    assert body["total_documents"] == 0


def test_knowledge_stats_are_tenant_scoped(client, auth_headers, registered_user, mock_embeddings):
    files = {"file": ("policy.txt", io.BytesIO(b"Tenant one policy text."), "text/plain")}
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert resp.status_code == 202

    other_user = {
        "email": "stats-other@acme-test.com",
        "full_name": "Stats Other",
        "password": "another-pass-1",
    }
    client.post("/api/v1/auth/register", json=other_user)
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other_user["email"], "password": other_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    mine = client.get("/api/v1/knowledge/stats", headers=auth_headers)
    theirs = client.get("/api/v1/knowledge/stats", headers=other_headers)
    assert mine.status_code == 200
    assert theirs.status_code == 200
    assert mine.json()["total_chunks"] >= 1
    assert theirs.json()["total_chunks"] == 0
