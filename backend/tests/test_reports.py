from datetime import datetime, timezone

from app.detection_engine import DetectionEngine
from app.detection_engine.samples import PY, rename_python
from app.reports.pdf import build_assignment_report, build_pair_report


def _pair_data():
    a, b = PY["bank_account"], rename_python(PY["bank_account"])
    res = DetectionEngine().compare(a, b, "python").to_dict()
    res.update(review_status="flagged", review_notes="Looks derived <b>& renamed</b>", override_score=None, reviewer="Dr. Rao", reviewed_at=datetime.now(timezone.utc))
    for s in res["segments"]:
        s.update(a_file="main.py", b_file="main.py")
    return {
        "assignment": {"title": "Bank <Account> lab", "language_key": "python", "deadline": None},
        "generated_at": datetime.now(timezone.utc), "generated_by": "Dr. Rao", "analyzed_at": datetime.now(timezone.utc),
        "student_a": "Asha", "student_b": "Ben", "submission_a": {"id": 1, "files": ["main.py"]}, "submission_b": {"id": 2, "files": ["main.py"]},
        "result": res, "files_a": {"main.py": a}, "files_b": {"main.py": b},
    }


def test_pair_report_is_valid_pdf_and_escapes_markup():
    pdf = build_pair_report(_pair_data())
    assert pdf.startswith(b"%PDF") and len(pdf) > 3000


def test_pair_report_without_segments():
    d = _pair_data()
    d["result"]["segments"] = []
    assert build_pair_report(d).startswith(b"%PDF")


def test_assignment_report():
    d = {
        "assignment": {"title": "Lab 1", "language_key": "java", "deadline": datetime.now(timezone.utc)},
        "generated_at": datetime.now(timezone.utc), "generated_by": "Admin",
        "stats": {"submissions": 3, "analyzed": 3, "pairs": 3, "average": 0.42, "flagged": 1, "review_threshold": 0.6},
        "rows": [{"student_a": "A", "student_b": "B", "overall": 0.9, "risk_level": "high", "confidence_label": "high", "review_status": "pending"}],
    }
    assert build_assignment_report(d).startswith(b"%PDF")
