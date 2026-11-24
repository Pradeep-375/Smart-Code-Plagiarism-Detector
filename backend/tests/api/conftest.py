"""API/integration test fixtures. Requires: pip install -r requirements-dev.txt

Uses an in-memory-style temporary SQLite database; PostgreSQL-specific behaviour is covered by running the
same suite against Postgres (DATABASE_URL=postgresql://... pytest) as described in docs/testing.md.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="scpds-test-")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ.setdefault("STORAGE_DIR", f"{_tmp}/storage")
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234567890")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@test.dev")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "AdminPass123")
os.environ.setdefault("USE_CELERY", "false")
os.environ.setdefault("FACULTY_REGISTRATION_CODE", "Faculty-Code-For-Tests-2026")

import io  # noqa: E402
import zipfile  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PW = "Passw0rdTest"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs lifespan: creates tables + seeds admin
        yield c


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_h(client):
    return _login(client, "admin@test.dev", "AdminPass123")


@pytest.fixture(scope="session")
def faculty_h(client, admin_h):
    r = client.post("/api/v1/users", headers=admin_h, json={"email": "fac@test.dev", "full_name": "Prof Test", "password": PW, "role": "faculty"})
    assert r.status_code == 201, r.text
    return _login(client, "fac@test.dev", PW)


@pytest.fixture(scope="session")
def faculty2_h(client, admin_h):
    client.post("/api/v1/users", headers=admin_h, json={"email": "fac2@test.dev", "full_name": "Prof Two", "password": PW, "role": "faculty"})
    return _login(client, "fac2@test.dev", PW)


def register_student(client, n):
    r = client.post("/api/v1/auth/register", json={"email": f"s{n}@test.dev", "full_name": f"Student {n}", "password": PW})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["id"]


@pytest.fixture(scope="session")
def students(client):
    return [register_student(client, n) for n in range(1, 5)]


def zip_bytes(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in entries.items():
            z.writestr(k, v)
    return buf.getvalue()
