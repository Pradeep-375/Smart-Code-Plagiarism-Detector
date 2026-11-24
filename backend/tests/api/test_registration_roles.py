"""Role-based registration, login and route protection (student / faculty / admin)."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.security import create_access_token
from tests.api.conftest import PW, _login

API = "/api/v1"
CODE = "Faculty-Code-For-Tests-2026"


def _reg(client, email, role=None, code=None, name="Test User", password=PW, **extra):
    body = {"email": email, "full_name": name, "password": password, **extra}
    if role is not None:
        body["role"] = role
    if code is not None:
        body["faculty_code"] = code
    return client.post(f"{API}/auth/register", json=body)


def _db_role(client, admin_h, email):
    r = client.get(f"{API}/users", headers=admin_h, params={"q": email})
    items = [u for u in r.json()["items"] if u["email"] == email.lower()]
    assert len(items) == 1, r.text
    return items[0]["role_name"]


# ---------------- registration ----------------
def test_default_registration_is_student(client, admin_h):
    r = _reg(client, "reg-default@test.dev")
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role_name"] == "student"
    assert _db_role(client, admin_h, "reg-default@test.dev") == "student"


def test_explicit_student_registration(client, admin_h):
    r = _reg(client, "reg-student@test.dev", role="student")
    assert r.status_code == 201 and r.json()["user"]["role_name"] == "student"
    assert _db_role(client, admin_h, "reg-student@test.dev") == "student"


def test_faculty_registration_with_code_stores_faculty_role(client, admin_h):
    """The reported bug: choosing Faculty used to produce a Student account."""
    r = _reg(client, "reg-faculty@test.dev", role="faculty", code=CODE)
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role_name"] == "faculty"
    assert _db_role(client, admin_h, "reg-faculty@test.dev") == "faculty"


@pytest.mark.parametrize("code", [None, "", "wrong-code", CODE + "x", CODE.lower()])
def test_faculty_registration_requires_correct_code(client, admin_h, code):
    email = f"reg-badcode-{abs(hash(str(code)))}@test.dev"
    r = _reg(client, email, role="faculty", code=code)
    assert r.status_code == 403, r.text
    # nothing was created, not even a student account
    assert client.get(f"{API}/users", headers=admin_h, params={"q": email}).json()["total"] == 0


def test_faculty_self_registration_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "faculty_registration_code", "")
    r = _reg(client, "reg-disabled@test.dev", role="faculty", code="anything")
    assert r.status_code == 403
    assert "not enabled" in r.json()["detail"]


@pytest.mark.parametrize("role", ["admin", "root", "superuser", "Faculty "])
def test_cannot_self_register_as_admin_or_unknown_role(client, admin_h, role):
    email = f"reg-priv-{abs(hash(role))}@test.dev"
    r = _reg(client, email, role=role, code=CODE)
    assert r.status_code == 422, r.text
    assert client.get(f"{API}/users", headers=admin_h, params={"q": email}).json()["total"] == 0


def test_duplicate_email_rejected_across_roles_and_case(client):
    assert _reg(client, "dup@test.dev").status_code == 201
    assert _reg(client, "dup@test.dev").status_code == 409
    assert _reg(client, "DUP@Test.Dev", role="faculty", code=CODE).status_code == 409


def test_registration_validation(client):
    assert _reg(client, "weak@test.dev", password="short1").status_code == 422
    assert _reg(client, "weak2@test.dev", password="allletterspw").status_code == 422
    assert _reg(client, "not-an-email").status_code == 422


# ---------------- login ----------------
@pytest.mark.parametrize("role,code", [("student", None), ("faculty", CODE)])
def test_login_returns_role_from_database(client, role, code):
    email = f"login-{role}@test.dev"
    assert _reg(client, email, role=role, code=code).status_code == 201
    r = client.post(f"{API}/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200
    assert r.json()["user"]["role_name"] == role
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"{API}/auth/me", headers=h).json()["role_name"] == role


def test_admin_login_and_role(client, admin_h):
    assert client.get(f"{API}/auth/me", headers=admin_h).json()["role_name"] == "admin"
    assert client.get(f"{API}/dashboard/admin", headers=admin_h).status_code == 200


def test_wrong_password_and_unknown_user_are_indistinguishable(client):
    _reg(client, "pw@test.dev")
    a = client.post(f"{API}/auth/login", json={"email": "pw@test.dev", "password": "Wrong1234"})
    b = client.post(f"{API}/auth/login", json={"email": "nobody@test.dev", "password": "Wrong1234"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_login_is_case_insensitive_on_email(client):
    _reg(client, "Mixed.Case@test.dev")
    assert client.post(f"{API}/auth/login", json={"email": "mixed.case@TEST.dev", "password": PW}).status_code == 200


def test_passwords_are_hashed(client):
    from app.database import SessionLocal
    from app.models import User
    from sqlalchemy import select
    _reg(client, "hash@test.dev")
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "hash@test.dev"))
        assert u.hashed_password.startswith("$2") and PW not in u.hashed_password


# ---------------- role is always taken from the database ----------------
def test_token_role_claim_is_not_trusted(client):
    """A validly signed token that *claims* admin must not grant admin to a student."""
    r = _reg(client, "claim@test.dev")
    forged = create_access_token(r.json()["user"]["id"], "admin")
    h = {"Authorization": f"Bearer {forged}"}
    assert client.get(f"{API}/users", headers=h).status_code == 403
    assert client.get(f"{API}/dashboard/admin", headers=h).status_code == 403
    assert client.get(f"{API}/admin/audit-logs", headers=h).status_code == 403


def test_garbage_and_wrongly_signed_tokens_rejected(client):
    import jwt
    bad = jwt.encode({"sub": "1", "exp": 9999999999}, "not-the-secret-key-not-the-secret-key-xx", algorithm="HS256")
    for tok in ("garbage", bad):
        assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_role_change_by_admin_applies_immediately(client, admin_h):
    r = _reg(client, "promote@test.dev")
    uid, h = r.json()["user"]["id"], {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"{API}/dashboard/faculty", headers=h).status_code == 403
    assert client.patch(f"{API}/users/{uid}", headers=admin_h, json={"role": "faculty"}).status_code == 200
    assert client.get(f"{API}/dashboard/faculty", headers=h).status_code == 200  # same token, new DB role
    assert client.patch(f"{API}/users/{uid}", headers=admin_h, json={"role": "student"}).status_code == 200
    assert client.get(f"{API}/dashboard/faculty", headers=h).status_code == 403


def test_deactivated_user_cannot_log_in_or_use_old_token(client, admin_h):
    r = _reg(client, "inactive@test.dev")
    uid, h = r.json()["user"]["id"], {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.delete(f"{API}/users/{uid}", headers=admin_h).status_code == 204
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "inactive@test.dev", "password": PW}).status_code == 401


def test_admin_cannot_demote_self(client, admin_h):
    me = client.get(f"{API}/auth/me", headers=admin_h).json()
    assert client.patch(f"{API}/users/{me['id']}", headers=admin_h, json={"role": "faculty"}).status_code == 400


def test_admin_creates_admin_and_faculty(client, admin_h):
    for role in ("admin", "faculty"):
        email = f"made-{role}@test.dev"
        r = client.post(f"{API}/users", headers=admin_h, json={"email": email, "full_name": "Made By Admin", "password": PW, "role": role})
        assert r.status_code == 201 and r.json()["role_name"] == role
        assert _login(client, email, PW)


# ---------------- route protection matrix ----------------
@pytest.fixture(scope="module")
def actors(client, admin_h):
    _reg(client, "m-student@test.dev")
    _reg(client, "m-faculty@test.dev", role="faculty", code=CODE)
    return {"anon": {}, "student": _login(client, "m-student@test.dev", PW),
            "faculty": _login(client, "m-faculty@test.dev", PW), "admin": admin_h}


# (method, path, {role: expected-status-class}); 2 = success, 4 = specific code listed
MATRIX = [
    ("GET", "/auth/me", {"anon": 401, "student": 200, "faculty": 200, "admin": 200}),
    ("GET", "/users", {"anon": 401, "student": 403, "faculty": 200, "admin": 200}),
    ("POST", "/users", {"anon": 401, "student": 403, "faculty": 403, "admin": 422}),
    ("GET", "/admin/audit-logs", {"anon": 401, "student": 403, "faculty": 403, "admin": 200}),
    ("GET", "/admin/settings/detection", {"anon": 401, "student": 403, "faculty": 403, "admin": 200}),
    ("GET", "/dashboard/admin", {"anon": 401, "student": 403, "faculty": 403, "admin": 200}),
    ("GET", "/dashboard/faculty", {"anon": 401, "student": 403, "faculty": 200, "admin": 200}),
    ("GET", "/dashboard/student", {"anon": 401, "student": 200, "faculty": 200, "admin": 200}),
    ("GET", "/assignments", {"anon": 401, "student": 200, "faculty": 200, "admin": 200}),
    ("POST", "/assignments", {"anon": 401, "student": 403, "faculty": 422, "admin": 422}),
    ("GET", "/submissions/mine", {"anon": 401, "student": 200, "faculty": 200, "admin": 200}),
    ("GET", "/results/999999", {"anon": 401, "student": 403, "faculty": 404, "admin": 404}),
    ("POST", "/analysis/compare", {"anon": 401, "student": 403, "faculty": 422, "admin": 422}),
    ("GET", "/notifications", {"anon": 401, "student": 200, "faculty": 200, "admin": 200}),
]


@pytest.mark.parametrize("method,path,expected", MATRIX, ids=[f"{m} {p}" for m, p, _ in MATRIX])
def test_route_access_matrix(client, actors, method, path, expected):
    for who, code in expected.items():
        r = client.request(method, f"{API}{path}", headers=actors[who], json={} if method == "POST" else None)
        assert r.status_code == code, f"{who} {method} {path}: expected {code}, got {r.status_code} {r.text[:200]}"


# ---------------- admin bootstrap CLI ----------------
def test_create_admin_cli_creates_and_refuses_duplicates():
    backend = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp}/cli.db", "STORAGE_DIR": f"{tmp}/s", "ADMIN_PASSWORD": "CliAdminPass1", "SEED_ADMIN_PASSWORD": ""}
        run = lambda *a: subprocess.run([sys.executable, "scripts/create_admin.py", *a], cwd=backend, env=env, capture_output=True, text=True)
        ok = run("--email", "cli@test.dev", "--name", "CLI Admin")
        assert ok.returncode == 0, ok.stderr
        assert "Created admin" in ok.stdout
        assert run("--email", "CLI@test.dev").returncode == 1  # exists -> refuse without --promote
        env["ADMIN_PASSWORD"] = "weak"
        assert run("--email", "other@test.dev").returncode == 1  # weak password rejected
