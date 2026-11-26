"""End-to-end tests for the resume upload/list/detail endpoints."""

from fastapi.testclient import TestClient

from pdf_utils import make_pdf

SAMPLE_TEXT = (
    "Alice Example\n"
    "alice@example.com\n"
    "\n"
    "Education\n"
    "B.Tech in Information Technology, NIT Trichy, 2025\n"
    "\n"
    "Skills\n"
    "Python, Django, PostgreSQL, Docker\n"
)

MAX_BYTES = 5 * 1024 * 1024


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str, text: str = SAMPLE_TEXT, filename: str = "resume.pdf"):
    pdf = make_pdf(text)
    return client.post(
        "/api/v1/resumes/upload",
        headers=_auth(token),
        files={"file": (filename, pdf, "application/pdf")},
    )


def _register(client: TestClient, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "User Two", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_extracts_structured_data(client, registered_user):
    token = registered_user["access_token"]
    response = _upload(client, token)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["original_filename"] == "resume.pdf"
    assert body["file_size"] > 0
    assert body["raw_text"]
    parsed = body["parsed_data"]
    assert parsed["name"] == "Alice Example"
    assert parsed["email"] == "alice@example.com"
    assert "Python" in parsed["programming_languages"]
    assert "Django" in parsed["frameworks"]
    assert "PostgreSQL" in parsed["databases"]
    assert "Docker" in parsed["tools"]
    assert any("B.Tech" in item for item in parsed["education"])


def test_upload_requires_auth(client):
    pdf = make_pdf(SAMPLE_TEXT)
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_rejects_non_pdf_extension(client, registered_user):
    response = _upload(client, registered_user["access_token"], filename="resume.txt")
    assert response.status_code == 400


def test_upload_rejects_invalid_magic_bytes(client, registered_user):
    response = client.post(
        "/api/v1/resumes/upload",
        headers=_auth(registered_user["access_token"]),
        files={"file": ("resume.pdf", b"hello world", "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_file(client, registered_user):
    response = client.post(
        "/api/v1/resumes/upload",
        headers=_auth(registered_user["access_token"]),
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(client, registered_user):
    big = b"%PDF-" + b"0" * MAX_BYTES
    response = client.post(
        "/api/v1/resumes/upload",
        headers=_auth(registered_user["access_token"]),
        files={"file": ("resume.pdf", big, "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_rejects_corrupted_pdf(client, registered_user):
    response = client.post(
        "/api/v1/resumes/upload",
        headers=_auth(registered_user["access_token"]),
        files={"file": ("resume.pdf", b"%PDF-1.4\nthis is not a real pdf", "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_rejects_pdf_without_text(client, registered_user):
    response = _upload(client, registered_user["access_token"], text="")
    assert response.status_code == 422


def test_list_and_detail(client, registered_user):
    token = registered_user["access_token"]

    first = _upload(client, token, text="Alice Example\nalice@example.com\n").json()
    second = _upload(
        client, token, text="Bob Example\nbob@example.com\nSkills\nGo, Redis\n"
    ).json()

    listing = client.get("/api/v1/resumes", headers=_auth(token))
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 2
    # Newest upload first.
    assert items[0]["id"] == second["id"]
    assert items[0]["name"] == "Bob Example"

    detail = client.get(f"/api/v1/resumes/{first['id']}", headers=_auth(token))
    assert detail.status_code == 200
    assert detail.json()["parsed_data"]["email"] == "alice@example.com"


def test_list_and_detail_require_auth(client):
    assert client.get("/api/v1/resumes").status_code == 401
    assert client.get("/api/v1/resumes/1").status_code == 401


def test_cannot_access_another_users_resume(client, registered_user):
    token_a = registered_user["access_token"]
    uploaded = _upload(client, token_a).json()

    other = _register(client, "other@example.com")
    token_b = other["access_token"]

    response = client.get(f"/api/v1/resumes/{uploaded['id']}", headers=_auth(token_b))
    assert response.status_code == 404

    listing_b = client.get("/api/v1/resumes", headers=_auth(token_b))
    assert listing_b.status_code == 200
    assert listing_b.json() == []


def test_get_unknown_resume_returns_404(client, registered_user):
    response = client.get("/api/v1/resumes/999999", headers=_auth(registered_user["access_token"]))
    assert response.status_code == 404
