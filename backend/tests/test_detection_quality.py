"""Regression benchmark: precision / recall / F1 on the labelled sample pairs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_engine import metrics, score_pairs  # noqa: E402

from app.detection_engine import DetectionConfig  # noqa: E402
from app.detection_engine.samples import build_eval_pairs  # noqa: E402


def test_quality_gates_at_default_threshold():
    cfg = DetectionConfig()
    scored = score_pairs(build_eval_pairs(), cfg)
    m = metrics(scored, cfg.thresholds["medium"])
    assert m["precision"] >= 0.95, m
    assert m["recall"] >= 0.95, m
    assert m["f1"] >= 0.95, m
    assert m["fpr"] <= 0.05, m


def test_category_expectations():
    cfg = DetectionConfig()
    by_cat: dict[str, list[float]] = {}
    for p, s in score_pairs(build_eval_pairs(), cfg):
        by_cat.setdefault(p.category, []).append(s)
    assert min(by_cat["identical"]) >= 99.9
    assert min(by_cat["reformatted"]) >= 85
    assert min(by_cat["renamed"]) >= 80
    assert min(by_cat["comments"]) >= 90
    assert min(by_cat["restructured"]) >= 50
    assert max(by_cat["different"]) < 30
    assert max(by_cat["hard_negative"]) < 40


def test_ml_layer_loads_and_is_monotonic():
    from app.detection_engine.ml import MLClassifier, feature_vector

    clf = MLClassifier.load()
    assert clf is not None
    hi = clf.predict_proba(feature_vector({k: 0.95 for k in DetectionConfig().weights}, 200, 150, 400))
    lo = clf.predict_proba(feature_vector({k: 0.1 for k in DetectionConfig().weights}, 200, 5, 400))
    assert hi > 0.5 > lo
