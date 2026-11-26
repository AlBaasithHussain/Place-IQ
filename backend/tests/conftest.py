"""Shared pytest fixtures.

By default tests run against an in-memory SQLite database (fast, no external
services). To run the identical suite against PostgreSQL, set TEST_DATABASE_URL:

    $env:TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/placement_prep_test"
    pytest
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register models on Base.metadata
from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

if TEST_DATABASE_URL and not TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)
else:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


@pytest.fixture(autouse=True)
def _prepare_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    payload = {
        "name": "Asha Verma",
        "email": "asha@example.com",
        "password": "Passw0rd1",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
