from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from pydantic import ValidationError

import app.api.routes.health as health_route
import app.api.routes.jobs as jobs_route
import app.api.routes.resumes as resumes_route
import app.services.resume.pdf as pdf_service
from app.core.config import JWT_AUDIENCE, JWT_ISSUER, Settings, settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.jobs.llm import LLMClient, LLMError
from app.services.resume.pdf import MAX_PDF_PAGES, MAX_PDF_TEXT_CHARS, PdfExtractionError
from pdf_utils import make_pdf

SAMPLE_TEXT = (
    "Alice Example\n"
    "alice@example.com\n"
    "Education\n"
    "B.Tech in Information Technology, NIT Trichy, 2025\n"
    "Skills\n"
    "Python, Django, PostgreSQL, Docker\n"
)


def _token_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "iat": now - timedelta(minutes=1),
        "exp": now + timedelta(minutes=30),
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
    }
    payload.update(overrides)
    return payload


def test_password_hash_is_bcrypt_and_never_plain():
    stored = hash_password("Passw0rd1")
    assert stored != "Passw0rd1"
    assert stored.startswith("$2b$12$")
    assert verify_password("Passw0rd1", stored)
    assert not verify_password("WrongPass1", stored)


def test_access_token_contains_required_security_claims():
    token = create_access_token(42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["aud"] == JWT_AUDIENCE
    assert payload["iss"] == JWT_ISSUER
    assert payload["iat"] <= payload["exp"]


def test_access_token_rejects_expired_signature():
    token = jwt.encode(
        _token_payload(
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
            exp=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_access_token_rejects_wrong_signature():
    token = jwt.encode(
        _token_payload(),
        "a-completely-different-signing-key",
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)


def test_access_token_rejects_alg_none():
    token = jwt.encode(_token_payload(), key="", algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_access_token_rejects_wrong_audience_and_issuer():
    wrong_audience = jwt.encode(
        _token_payload(aud="another-app"),
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    wrong_issuer = jwt.encode(
        _token_payload(iss="another-issuer"),
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(wrong_audience)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(wrong_issuer)


def test_access_token_requires_all_claims():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_me_rejects_tampered_token(client, registered_user):
    token = registered_user["access_token"]
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401


def test_orm_login_rejects_sql_injection_payload(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com' OR '1'='1", "password": "Passw0rd1"},
    )
    assert response.status_code in {401, 422}
    assert "access_token" not in response.json()


def test_cors_allows_only_configured_origins(client):
    allowed = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in allowed.headers

    blocked = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_settings_reject_weak_production_secret_and_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short",
            BACKEND_CORS_ORIGINS="http://localhost:5173",
            DATABASE_URL="sqlite:///test.db",
        )
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="development",
            SECRET_KEY="development-only-key",
            BACKEND_CORS_ORIGINS="*",
        )


def test_settings_normalizes_hosted_postgres_url_scheme():
    settings = Settings(DATABASE_URL="postgres://user:pass@db.example.com:5432/preppilot")
    assert settings.DATABASE_URL == "postgresql://user:pass@db.example.com:5432/preppilot"


def test_settings_reject_insecure_llm_base_url_when_key_present():
    with pytest.raises(ValidationError):
        Settings(LLM_API_KEY="sk-test-key", LLM_BASE_URL="http://evil.example/v1")


def test_llm_client_rejects_insecure_base_url():
    with pytest.raises(LLMError):
        LLMClient("sk-test-key", "http://evil.example/v1", "gpt-4o-mini", 5.0)


def test_llm_error_does_not_leak_api_key(monkeypatch):
    secret = "sk-super-secret-value"
    client = LLMClient(secret, "http://localhost:9999/v1", "gpt-4o-mini", 1.0)

    def fail(*args, **kwargs):
        raise httpx.ConnectError(f"connection failed with {kwargs['headers']['Authorization']}")

    monkeypatch.setattr("app.services.jobs.llm.httpx.post", fail)
    with pytest.raises(LLMError) as exc_info:
        client.complete_json("system", "user")
    assert secret not in str(exc_info.value)


def test_ai_failure_response_does_not_leak_details(client, registered_user, monkeypatch):
    from app.services.jobs.analyzer import JobAnalysisError

    def fail(_text):
        raise JobAnalysisError("sk-super-secret-value")

    monkeypatch.setattr(jobs_route.analyzer, "analyze_job_description", fail)
    response = client.post(
        "/api/v1/jobs/analyze",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        json={"text": "Senior Python Developer with FastAPI SQL Docker AWS experience."},
    )
    assert response.status_code == 502
    assert "sk-super-secret-value" not in response.text
    assert response.json()["detail"] == "AI service failed. Please try again."


def test_database_health_does_not_leak_driver_details(client, monkeypatch):
    def fail():
        raise RuntimeError("postgresql://user:password@secret-host/db")

    monkeypatch.setattr(health_route, "check_database", fail)
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert "detail" not in body
    assert "password" not in response.text


def test_upload_sanitizes_filename_and_forces_pdf_mime(client, registered_user):
    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        files={
            "file": (
                "C:\\tmp\\..\\evil resume.pdf",
                make_pdf(SAMPLE_TEXT),
                "text/html",
            )
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["original_filename"] == "evil resume.pdf"
    assert body["mime_type"] == "application/pdf"


def test_upload_accepts_exact_size_limit(client, registered_user, monkeypatch):
    monkeypatch.setattr(resumes_route, "extract_text_from_pdf", lambda _data: SAMPLE_TEXT)
    data = b"%PDF-" + b" " * (resumes_route.MAX_UPLOAD_BYTES - 5)
    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        files={"file": ("resume.pdf", data, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["file_size"] == resumes_route.MAX_UPLOAD_BYTES


class _FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, pages: list[_FakePage], encrypted: bool = False):
        self.pages = pages
        self.is_encrypted = encrypted


def test_pdf_extraction_rejects_excessive_pages(monkeypatch):
    monkeypatch.setattr(
        pdf_service,
        "PdfReader",
        lambda _stream: _FakeReader([_FakePage("x")] * (MAX_PDF_PAGES + 1)),
    )
    with pytest.raises(PdfExtractionError, match="too many pages"):
        pdf_service.extract_text_from_pdf(b"%PDF-1.4 test")


def test_pdf_extraction_rejects_excessive_text(monkeypatch):
    monkeypatch.setattr(
        pdf_service,
        "PdfReader",
        lambda _stream: _FakeReader(
            [_FakePage("x" * MAX_PDF_TEXT_CHARS), _FakePage("y")]
        ),
    )
    with pytest.raises(PdfExtractionError, match="too much text"):
        pdf_service.extract_text_from_pdf(b"%PDF-1.4 test")
