"""End-to-end tests for the protected student profile endpoints."""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_profile_get_default_after_register(client, registered_user):
    response = client.get(
        "/api/v1/profile/me", headers=_auth(registered_user["access_token"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == registered_user["user"]["id"]
    assert body["college"] is None
    assert body["graduation_year"] is None


def test_profile_update_and_persist(client, registered_user):
    headers = _auth(registered_user["access_token"])
    payload = {
        "college": "IIT Delhi",
        "degree": "B.Tech",
        "branch": "CSE",
        "graduation_year": 2026,
        "target_role": "Backend Engineer",
    }
    response = client.put("/api/v1/profile/me", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    for key, value in payload.items():
        assert body[key] == value

    again = client.get("/api/v1/profile/me", headers=headers)
    assert again.status_code == 200
    assert again.json()["college"] == "IIT Delhi"


def test_profile_partial_update_keeps_other_fields(client, registered_user):
    headers = _auth(registered_user["access_token"])
    client.put(
        "/api/v1/profile/me",
        json={"college": "IIT Delhi", "degree": "B.Tech"},
        headers=headers,
    )
    response = client.put("/api/v1/profile/me", json={"branch": "ECE"}, headers=headers)
    body = response.json()
    assert body["college"] == "IIT Delhi"
    assert body["degree"] == "B.Tech"
    assert body["branch"] == "ECE"


def test_profile_rejects_invalid_graduation_year(client, registered_user):
    headers = _auth(registered_user["access_token"])
    response = client.put(
        "/api/v1/profile/me", json={"graduation_year": 1900}, headers=headers
    )
    assert response.status_code == 422


def test_profile_requires_auth(client):
    assert client.get("/api/v1/profile/me").status_code == 401
    assert client.put("/api/v1/profile/me", json={"college": "X"}).status_code == 401
