"""Tests for registration, login, and profile endpoints."""


def test_register_creates_user(client, user_payload):
    resp = client.post("/api/v1/auth/register", json=user_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == user_payload["email"]
    assert body["full_name"] == user_payload["full_name"]
    assert "hashed_password" not in body  # Never leak the hash through the API
    assert "password" not in body


def test_register_duplicate_email_rejected(client, user_payload):
    client.post("/api/v1/auth/register", json=user_payload)
    resp = client.post("/api/v1/auth/register", json=user_payload)

    assert resp.status_code == 409


def test_register_rejects_weak_password(client, user_payload):
    user_payload["password"] = "onlyletters"  # No digit
    resp = client.post("/api/v1/auth/register", json=user_payload)

    assert resp.status_code == 422


def test_register_rejects_short_password(client, user_payload):
    user_payload["password"] = "a1"
    resp = client.post("/api/v1/auth/register", json=user_payload)

    assert resp.status_code == 422


def test_login_succeeds_with_correct_credentials(client, user_payload, registered_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_fails_with_wrong_password(client, user_payload, registered_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": "wrong-password-1"},
    )

    assert resp.status_code == 401


def test_login_fails_for_nonexistent_account(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.com", "password": "whatever-1"},
    )

    assert resp.status_code == 401


def test_get_profile_requires_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_get_profile_returns_current_user(client, auth_headers, user_payload):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["email"] == user_payload["email"]


def test_get_profile_rejects_garbage_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_swagger_authorization_uses_form_login(client, user_payload, registered_user):
    schema = client.get("/openapi.json").json()
    token_url = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"]
    response = client.post(token_url, data={"username": user_payload["email"], "password": user_payload["password"]})
    assert response.status_code == 200
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert profile.json()["id"] == registered_user["id"]
