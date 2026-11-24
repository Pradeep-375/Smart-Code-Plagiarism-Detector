"""API tests: auth, RBAC, assignments, uploads, analysis, review, student privacy.

These need `pip install -r requirements-dev.txt`; they are skipped when FastAPI is not installed.
Tests share one session-scoped app/database and run in file order.
"""
import pytest

from app.detection_engine import samples as S
from tests.api.conftest import PW, register_student, zip_bytes

API = "/api/v1"
state: dict = {}


def py(name):
    return S.PY[name]


# ---------- health & auth ----------
def test_health(client):
    assert client.get(f"{API}/health").status_code == 200


def test_login_wrong_password_rejected(client, admin_h):
    r = client.post(f"{API}/auth/login", json={"email": "admin@test.dev", "password": "WrongPass123"})
    assert r.status_code == 401


def test_register_rejects_weak_password(client):
    r = client.post(f"{API}/auth/register", json={"email": "weak@test.dev", "full_name": "Weak User", "password": "short"})
    assert r.status_code == 422


def test_register_duplicate_email(client, students):
    r = client.post(f"{API}/auth/register", json={"email": "s1@test.dev", "full_name": "Dup", "password": PW})
    assert r.status_code in (400, 409)


def test_me_requires_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401


def test_me_returns_profile(client, faculty_h):
    r = client.get(f"{API}/auth/me", headers=faculty_h)
    assert r.status_code == 200 and r.json()["role_name"] == "faculty"


def test_change_password(client, students):
    h, _ = students[3]
    r = client.post(f"{API}/auth/change-password", headers=h, json={"current_password": PW, "new_password": "NewPassw0rd9"})
    assert r.status_code in (200, 204)
    r = client.post(f"{API}/auth/login", json={"email": "s4@test.dev", "password": "NewPassw0rd9"})
    assert r.status_code == 200


# ---------- RBAC ----------
def test_students_cannot_list_users(client, students):
    assert client.get(f"{API}/users", headers=students[0][0]).status_code == 403


def test_faculty_cannot_manage_users(client, faculty_h):
    r = client.post(f"{API}/users", headers=faculty_h, json={"email": "x@test.dev", "full_name": "X Y", "password": PW, "role": "admin"})
    assert r.status_code == 403


def test_admin_lists_users_and_audit_logs(client, admin_h, faculty_h):
    assert client.get(f"{API}/users", headers=admin_h).json()["total"] >= 2
    logs = client.get(f"{API}/admin/audit-logs", headers=admin_h)
    assert logs.status_code == 200 and logs.json()["total"] >= 1


def test_audit_logs_forbidden_for_faculty(client, faculty_h):
    assert client.get(f"{API}/admin/audit-logs", headers=faculty_h).status_code == 403


# ---------- assignments ----------
def test_student_cannot_create_assignment(client, students):
    r = client.post(f"{API}/assignments", headers=students[0][0], json={"title": "Nope", "language_key": "python"})
    assert r.status_code == 403


def test_create_assignment_validation(client, faculty_h):
    assert client.post(f"{API}/assignments", headers=faculty_h, json={"title": "ab", "language_key": "python"}).status_code == 422
    r = client.post(f"{API}/assignments", headers=faculty_h, json={"title": "Bad lang", "language_key": "cobol"})
    assert r.status_code == 400
    r = client.post(f"{API}/assignments", headers=faculty_h, json={"title": "Thresholds", "language_key": "python", "review_threshold": 0.8, "high_threshold": 0.4})
    assert r.status_code == 400


def test_create_assignment(client, faculty_h):
    r = client.post(f"{API}/assignments", headers=faculty_h, json={"title": "Prime tools", "description": "Write prime helpers", "language_key": "python"})
    assert r.status_code == 201, r.text
    state["aid"] = r.json()["id"]


def test_other_faculty_cannot_access(client, faculty2_h):
    assert client.get(f"{API}/assignments/{state['aid']}", headers=faculty2_h).status_code in (403, 404)
    assert client.post(f"{API}/assignments/{state['aid']}/analyze", headers=faculty2_h).status_code in (403, 404)


# ---------- uploads ----------
def _upload(client, headers, files, **data):
    return client.post(f"{API}/assignments/{state['aid']}/submissions", headers=headers, files=files, data=data)


def test_student_upload_single_file(client, students):
    (h, _), code = students[0], py("prime_tools")
    r = _upload(client, h, [("files", ("prime.py", code.encode(), "text/plain"))])
    assert r.status_code == 201, r.text


def test_upload_rejects_disallowed_extension(client, students):
    r = _upload(client, students[1][0], [("files", ("evil.exe", b"MZ", "application/octet-stream"))])
    assert r.status_code in (400, 415, 422)


def test_upload_rejects_path_traversal_zip(client, students):
    z = zip_bytes({"../../evil.py": "print(1)"})
    r = _upload(client, students[1][0], [("files", ("s.zip", z, "application/zip"))])
    assert r.status_code in (200, 201, 400, 422)
    if r.status_code in (200, 201):
        assert all(".." not in f["filename"] for f in r.json().get("files", []))


def test_upload_zip_of_sources(client, students):
    z = zip_bytes({"prime/main.py": S.rename_python(py("prime_tools")) if hasattr(S, "rename_python") else py("prime_tools")})
    r = _upload(client, students[1][0], [("files", ("s.zip", z, "application/zip"))])
    assert r.status_code == 201, r.text


def test_student_cannot_upload_for_others(client, students):
    # student_id from a student is ignored: the upload is always attributed to the caller
    h, uid = students[2]
    r = _upload(client, h, [("files", ("p.py", py("grade_report").encode(), "text/plain"))], student_id="1")
    assert r.status_code == 201
    assert r.json()["student_id"] == uid


def test_faculty_uploads_on_behalf(client, faculty_h, admin_h):
    _, sid = register_student(client, 9)
    r = _upload(client, faculty_h, [("files", ("p.py", S.reformat_python(py("prime_tools")).encode(), "text/plain"))], student_id=str(sid))
    assert r.status_code == 201, r.text


# ---------- analysis ----------
def test_run_analysis_and_poll(client, faculty_h):
    r = client.post(f"{API}/assignments/{state['aid']}/analyze", headers=faculty_h)
    assert r.status_code == 202, r.text
    jid = r.json()["id"]
    j = client.get(f"{API}/analysis/jobs/{jid}", headers=faculty_h).json()
    assert j["status"] in ("queued", "running", "completed")
    assert j["status"] == "completed"  # BackgroundTasks run before the TestClient returns


def test_results_listed_and_flag_copy(client, faculty_h):
    r = client.get(f"{API}/assignments/{state['aid']}/results", headers=faculty_h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "expected at least one compared pair"
    top = items[0]
    assert top["overall"] >= 0.5
    assert top["review_status"] == "pending"  # similarity is never auto-confirmed
    state["rid"] = top["id"]


def test_matrix_available(client, faculty_h):
    assert client.get(f"{API}/assignments/{state['aid']}/matrix", headers=faculty_h).status_code == 200


def test_result_detail_has_explanations(client, faculty_h):
    d = client.get(f"{API}/results/{state['rid']}", headers=faculty_h).json()
    assert d["scores"] and d.get("disclaimer", True)


def test_review_workflow(client, faculty_h):
    r = client.patch(f"{API}/results/{state['rid']}/review", headers=faculty_h, json={"review_status": "confirmed", "notes": "checked manually"})
    assert r.status_code == 200 and r.json()["review_status"] == "confirmed"


def test_invalid_review_status_rejected(client, faculty_h):
    assert client.patch(f"{API}/results/{state['rid']}/review", headers=faculty_h, json={"review_status": "guilty"}).status_code == 422


def test_students_cannot_view_results(client, students):
    assert client.get(f"{API}/results/{state['rid']}", headers=students[0][0]).status_code == 403
    assert client.get(f"{API}/assignments/{state['aid']}/results", headers=students[0][0]).status_code == 403


def test_student_feedback_hides_peer_identity(client, students):
    subs = client.get(f"{API}/submissions/mine", headers=students[0][0]).json()
    items = subs["items"] if isinstance(subs, dict) else subs
    assert items
    r = client.get(f"{API}/submissions/{items[0]['id']}/feedback", headers=students[0][0])
    assert r.status_code == 200
    assert "Student 2" not in r.text and "s2@test.dev" not in r.text


def test_compare_endpoint(client, faculty_h):
    r = client.post(f"{API}/analysis/compare", headers=faculty_h, json={"language": "python", "code_a": py("prime_tools"), "code_b": S.reformat_python(py("prime_tools"))})
    assert r.status_code in (200, 422)


def test_pdf_and_csv_exports(client, faculty_h):
    pdf = client.get(f"{API}/results/{state['rid']}/report.pdf", headers=faculty_h)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    csv = client.get(f"{API}/assignments/{state['aid']}/export.csv", headers=faculty_h)
    assert csv.status_code == 200 and "overall" in csv.text.lower()


# ---------- dashboards & notifications ----------
@pytest.mark.parametrize("who,path", [("admin_h", "admin"), ("faculty_h", "faculty")])
def test_staff_dashboards(client, request, who, path):
    assert client.get(f"{API}/dashboard/{path}", headers=request.getfixturevalue(who)).status_code == 200


def test_student_dashboard_and_role_isolation(client, students, faculty_h):
    assert client.get(f"{API}/dashboard/student", headers=students[0][0]).status_code == 200
    assert client.get(f"{API}/dashboard/admin", headers=faculty_h).status_code == 403


def test_notifications_read_all(client, students):
    h = students[0][0]
    assert client.get(f"{API}/notifications", headers=h).status_code == 200
    assert client.post(f"{API}/notifications/read-all", headers=h).status_code in (200, 204)


def test_admin_detection_settings_roundtrip(client, admin_h):
    cur = client.get(f"{API}/admin/settings/detection", headers=admin_h).json()
    r = client.put(f"{API}/admin/settings/detection", headers=admin_h, json={"weights": cur["weights"], "review_threshold": 0.5, "high_threshold": 0.75})
    assert r.status_code == 200
