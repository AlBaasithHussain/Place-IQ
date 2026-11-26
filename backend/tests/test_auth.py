"""End-to-end tests for every authentication endpoint."""

from app.core.security import create_access_token, verify_password
from app.models.user import User


def _payload(**overrides):
    data = {
        "name": "Asha Verma",
        "email": "asha@example.com",
        "password": "Passw0rd1",
    }
    data.update(overrides)
    return data


def test_register_returns_token_and_public_user(client):
    response = client.post("/api/v1/auth/register", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["name"] == "Asha Verma"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_register_never_stores_plaintext(client, db_session):
    client.post("/api/v1/auth/register", json=_payload())
    user = db_session.query(User).filter(User.email == "asha@example.com").one()
    assert user.password_hash != "Passw0rd1"
    assert user.password_hash.startswith("$2")
    assert verify_password("Passw0rd1", user.password_hash)


def test_register_duplicate_email_conflict(client):
    assert client.post("/api/v1/auth/register", json=_payload()).status_code == 201
    response = client.post("/api/v1/auth/register", json=_payload(name="Someone Else"))
    assert response.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post("/api/v1/auth/register", json=_payload(email="not-an-email"))
    assert response.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post("/api/v1/auth/register", json=_payload(password="Ab1"))
    assert response.status_code == 422


def test_register_rejects_weak_password(client):
    response = client.post("/api/v1/auth/register", json=_payload(password="onlyletters"))
    assert response.status_code == 422


def test_login_success(client):
    client.post("/api/v1/auth/register", json=_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "Passw0rd1"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_is_email_case_insensitive(client):
    client.post("/api/v1/auth/register", json=_payload(email="Asha@Example.com"))
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "Passw0rd1"},
    )
    assert response.status_code == 200


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json=_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Passw0rd1"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_valid_token(client, registered_user):
    token = registered_user["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "asha@example.com"
    assert response.json()["id"] == registered_user["user"]["id"]


def test_me_rejects_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


def test_me_rejects_token_for_missing_user(client):
    token = create_access_token(999999)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_logout_requires_auth(client):
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_logout_with_token(client, registered_user):
    token = registered_user["access_token"]
    response = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "detail" in response.json()
