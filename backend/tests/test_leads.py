"""Tests for lead creation, AI qualification, and status management."""

import json


def _lead_payload(**overrides):
    payload = {
        "company_name": "Northwind Traders",
        "contact_name": "Sam Lee",
        "contact_email": "sam@northwind-test.com",
        "industry": "Retail",
        "company_size": "smb",
        "budget_range": "$10k-$50k",
        "pain_points": "Manual invoice processing is slow and error-prone.",
        "source": "website",
    }
    payload.update(overrides)
    return payload


def test_create_lead(client, auth_headers):
    resp = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "Northwind Traders"
    assert body["status"] == "new"
    assert body["qualification_score"] is None


def test_create_lead_requires_auth(client):
    resp = client.post("/api/v1/leads", json=_lead_payload())
    assert resp.status_code == 401


def test_qualify_lead_scores_and_drafts_email(client, auth_headers, fake_chat_responses):
    create_resp = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload())
    lead_id = create_resp.json()["id"]

    qualification = {
        "score": 82,
        "reasoning": "Strong budget fit and a clear, well-defined pain point.",
        "recommended_action": "pursue",
        "strengths": ["Budget confirmed", "Clear pain point"],
        "concerns": ["No confirmed timeline"],
        "next_steps": ["Schedule a discovery call"],
        "confidence_score": 0.9,
    }
    email = {
        "subject": "Cutting invoice processing time at Northwind Traders",
        "body": "Hi Sam,\n\nSaw that manual invoice processing has been a pain point...",
        "tone": "confident, urgent, and value-focused",
    }
    fake_chat_responses(
        "services.lead_service.openai_client.chat.completions.create",
        [json.dumps(qualification), json.dumps(email)],
    )

    resp = client.post(f"/api/v1/leads/{lead_id}/qualify", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["qualification_score"] == 82
    assert body["recommended_action"] == "pursue"
    assert body["status"] == "qualified"
    assert "Northwind Traders" in body["email_subject"]


def test_qualify_lead_survives_malformed_email_draft(client, auth_headers, fake_chat_responses):
    """A malformed email-draft response shouldn't fail the whole request —
    qualification already succeeded and is the more important half."""
    create_resp = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload())
    lead_id = create_resp.json()["id"]

    qualification = {
        "score": 55,
        "reasoning": "Moderate fit.",
        "recommended_action": "nurture",
        "strengths": ["Responsive contact"],
        "concerns": ["Budget unclear"],
        "next_steps": ["Send case study"],
        "confidence_score": 0.6,
    }
    fake_chat_responses(
        "services.lead_service.openai_client.chat.completions.create",
        [json.dumps(qualification), "this is not valid json"],
    )

    resp = client.post(f"/api/v1/leads/{lead_id}/qualify", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["qualification_score"] == 55
    assert resp.json()["drafted_email"] is not None


def test_list_leads_filters_by_min_score(client, auth_headers, fake_chat_responses):
    low = client.post(
        "/api/v1/leads", headers=auth_headers, json=_lead_payload(company_name="LowFit Co")
    ).json()
    high = client.post(
        "/api/v1/leads", headers=auth_headers, json=_lead_payload(company_name="HighFit Co")
    ).json()

    fake_chat_responses(
        "services.lead_service.openai_client.chat.completions.create",
        [
            json.dumps({
                "score": 20, "reasoning": "Poor fit.", "recommended_action": "disqualify",
                "strengths": [], "concerns": ["No budget"], "next_steps": [], "confidence_score": 0.5,
            }),
            json.dumps({"subject": "Following up", "body": "...", "tone": "brief"}),
        ],
    )
    client.post(f"/api/v1/leads/{low['id']}/qualify", headers=auth_headers)

    fake_chat_responses(
        "services.lead_service.openai_client.chat.completions.create",
        [
            json.dumps({
                "score": 90, "reasoning": "Great fit.", "recommended_action": "pursue",
                "strengths": ["Budget", "Authority"], "concerns": [], "next_steps": ["Call"],
                "confidence_score": 0.95,
            }),
            json.dumps({"subject": "Let's talk", "body": "...", "tone": "confident"}),
        ],
    )
    client.post(f"/api/v1/leads/{high['id']}/qualify", headers=auth_headers)

    resp = client.get("/api/v1/leads?status=qualified&min_score=50", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["leads"][0]["company_name"] == "HighFit Co"


def test_update_lead_status(client, auth_headers):
    lead_id = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload()).json()["id"]

    resp = client.patch(f"/api/v1/leads/{lead_id}/status?status=contacted", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "contacted"


def test_update_lead_status_rejects_invalid_value(client, auth_headers):
    lead_id = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload()).json()["id"]

    resp = client.patch(f"/api/v1/leads/{lead_id}/status?status=not-a-real-status", headers=auth_headers)

    assert resp.status_code == 400


def test_delete_lead(client, auth_headers):
    lead_id = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload()).json()["id"]

    resp = client.delete(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert resp.status_code == 200

    list_resp = client.get("/api/v1/leads", headers=auth_headers)
    assert list_resp.json()["total"] == 0


def test_lead_not_found_returns_404(client, auth_headers):
    resp = client.post("/api/v1/leads/does-not-exist/qualify", headers=auth_headers)
    assert resp.status_code == 404


def test_email_outage_preserves_zero_score_and_dashboard_average(
    client, auth_headers, monkeypatch,
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    lead_id = client.post("/api/v1/leads", headers=auth_headers, json=_lead_payload()).json()["id"]
    qualification = {"score": 0, "reasoning": "No fit", "recommended_action": "disqualify",
                     "strengths": [], "concerns": ["No budget"], "next_steps": []}
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(qualification)))])
    monkeypatch.setattr("services.lead_service._call_model",
                        Mock(side_effect=[response, ConnectionError("email unavailable")]))
    qualified = client.post(f"/api/v1/leads/{lead_id}/qualify", headers=auth_headers)
    assert qualified.status_code == 200
    assert qualified.json()["qualification_score"] == 0
    assert "write manually" in qualified.json()["drafted_email"]
    assert client.get("/api/v1/leads", headers=auth_headers).json()["avg_score"] == 0
    assert client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()["avg_lead_score"] == 0
