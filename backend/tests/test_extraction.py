"""Tests for structured data extraction from documents."""

import io
import json

import pytest


def _upload_and_wait(client, auth_headers, content="Invoice #1001 for services rendered."):
    """Upload a document and return its (doc_id, final_status) once Celery's
    eager-mode processing has finished. The upload response itself always
    reports "pending" — that's the state at creation time, by design (see
    api/routes/documents.py) — so we re-fetch to see the real status."""
    files = {"file": ("invoice.txt", io.BytesIO(content.encode()), "text/plain")}
    resp = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    doc_id = resp.json()["id"]

    detail = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    return doc_id, detail.json()["status"]


def _upload_ready_document(client, auth_headers, mock_embeddings, content="Invoice #1001 for services rendered."):
    doc_id, status = _upload_and_wait(client, auth_headers, content)
    assert status == "ready", f"expected document to finish ready, got {status!r}"
    return doc_id


def test_extract_invoice_data(client, auth_headers, mock_embeddings, fake_chat_responses):
    doc_id = _upload_ready_document(client, auth_headers, mock_embeddings)

    invoice_json = {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-06-01",
        "due_date": "2026-06-30",
        "vendor_name": "Acme Services LLC",
        "vendor_address": None,
        "vendor_email": None,
        "client_name": "Northwind Traders",
        "client_address": None,
        "line_items": [
            {"description": "Consulting hours", "quantity": 10, "unit_price": 150, "total_price": 1500}
        ],
        "subtotal": 1500,
        "tax_amount": 120,
        "tax_rate": 8,
        "total_amount": 1620,
        "currency": "USD",
        "payment_terms": "Net 30",
        "notes": None,
        "confidence_score": 0.95,
    }
    fake_chat_responses(
        "services.extraction_service.openai_client.chat.completions.create",
        [json.dumps(invoice_json)],
    )

    resp = client.post(
        "/api/v1/extraction/run",
        headers=auth_headers,
        json={"document_id": doc_id, "document_type": "invoice"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted_data"]["invoice_number"] == "INV-1001"
    assert body["extracted_data"]["total_amount"] == 1620
    assert body["confidence_score"] == 0.95


@pytest.mark.parametrize("output", [
    "not valid json at all", "[]", '{"confidence_score": "high"}',
    '{"confidence_score": 1.5}', '{"confidence_score": "NaN"}',
])
def test_extract_rejects_malformed_model_output(client, auth_headers, mock_embeddings, fake_chat_responses, output):
    doc_id = _upload_ready_document(client, auth_headers, mock_embeddings)

    fake_chat_responses(
        "services.extraction_service.openai_client.chat.completions.create",
        [output],
    )

    resp = client.post(
        "/api/v1/extraction/run",
        headers=auth_headers,
        json={"document_id": doc_id, "document_type": "invoice"},
    )

    assert resp.status_code == 422
    assert client.get(f"/api/v1/extraction/document/{doc_id}", headers=auth_headers).json() == []


def test_extract_requires_document_to_be_ready(client, auth_headers, mock_embeddings, fake_chat_responses):
    # An empty document fails processing and never reaches "ready".
    doc_id, status = _upload_and_wait(client, auth_headers, content="   ")
    assert status == "failed"

    resp = client.post(
        "/api/v1/extraction/run",
        headers=auth_headers,
        json={"document_id": doc_id, "document_type": "invoice"},
    )

    assert resp.status_code == 400


def test_list_extractions_for_document(client, auth_headers, mock_embeddings, fake_chat_responses):
    doc_id = _upload_ready_document(client, auth_headers, mock_embeddings)

    receipt_json = {
        "merchant_name": "Corner Cafe",
        "merchant_address": None,
        "transaction_date": "2026-06-01",
        "transaction_time": "09:15",
        "items": [{"description": "Coffee", "quantity": 2, "unit_price": 4.5, "total_price": 9.0}],
        "subtotal": 9.0,
        "tax_amount": 0.75,
        "tip_amount": 1.5,
        "total_amount": 11.25,
        "payment_method": "credit_card",
        "receipt_number": "R-42",
        "category": "Meals",
        "confidence_score": 0.88,
    }
    fake_chat_responses(
        "services.extraction_service.openai_client.chat.completions.create",
        [json.dumps(receipt_json)],
    )
    client.post(
        "/api/v1/extraction/run",
        headers=auth_headers,
        json={"document_id": doc_id, "document_type": "receipt"},
    )

    resp = client.get(f"/api/v1/extraction/document/{doc_id}", headers=auth_headers)

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["document_type"] == "receipt"
