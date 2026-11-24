"""Train the optional ML classifier on synthetic labelled pairs and save model_weights.json.

    python scripts/train_ml.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.detection_engine import DetectionConfig, compare_prepared, prepare_file  # noqa: E402
from app.detection_engine.ml import WEIGHTS_PATH, MLClassifier, feature_vector, train  # noqa: E402
from app.detection_engine.samples import build_eval_pairs, build_training_pairs  # noqa: E402


def featurize(pairs, cfg):
    X, y = [], []
    for p in pairs:
        a = prepare_file(p.a, p.language, "A", cfg)
        b = prepare_file(p.b, p.language, "B", cfg)
        r = compare_prepared(a, b, cfg)
        X.append(feature_vector(r.scores, r.min_tokens, r.details["token"]["longest_match"],
                                r.details["token"]["tokens_a"] + r.details["token"]["tokens_b"]))
        y.append(p.label)
    return X, y


def main() -> None:
    cfg = DetectionConfig()
    Xtr, ytr = featurize(build_training_pairs(), cfg)
    model = train(Xtr, ytr)
    WEIGHTS_PATH.write_text(json.dumps(model, indent=2))
    clf = MLClassifier(model)
    Xte, yte = featurize(build_eval_pairs(), cfg)
    preds = [1 if clf.predict_proba(x) >= 0.5 else 0 for x in Xte]
    tp = sum(1 for p, t in zip(preds, yte) if p and t)
    fp = sum(1 for p, t in zip(preds, yte) if p and not t)
    fn = sum(1 for p, t in zip(preds, yte) if not p and t)
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    print(f"trained on {len(ytr)} pairs; held-out: precision={prec:.3f} recall={rec:.3f} (n={len(yte)})")
    print(f"weights written to {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
