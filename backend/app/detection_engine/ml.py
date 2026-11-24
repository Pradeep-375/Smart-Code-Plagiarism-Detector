"""Optional machine-learning layer: a tiny logistic-regression classifier.

It is trained on the *algorithm scores* (not on raw code) and outputs an extra
``ml_probability`` that is shown next to - never instead of - the explainable weighted score.
Pure Python, no extra dependencies.  Weights live in ``model_weights.json``.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .scoring import ALGORITHMS

FEATURES = list(ALGORITHMS) + ["size_factor", "longest_ratio"]
WEIGHTS_PATH = Path(__file__).with_name("model_weights.json")


def feature_vector(scores: dict[str, float], min_tokens: int, longest_match: int, tokens_total: int) -> list[float]:
    size_factor = min(1.0, min_tokens / 120.0)
    longest_ratio = min(1.0, (2.0 * longest_match / tokens_total)) if tokens_total else 0.0
    return [scores.get(a, 0.0) for a in ALGORITHMS] + [size_factor, longest_ratio]


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def train(X: list[list[float]], y: list[int], epochs: int = 1500, lr: float = 0.3, l2: float = 0.01, seed: int = 7) -> dict:
    rng = random.Random(seed)
    n, d = len(X), len(X[0])
    w = [rng.uniform(-0.01, 0.01) for _ in range(d)]
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * d
        gb = 0.0
        for xi, yi in zip(X, y):
            p = _sigmoid(sum(wj * xj for wj, xj in zip(w, xi)) + b)
            err = p - yi
            for j in range(d):
                gw[j] += err * xi[j]
            gb += err
        for j in range(d):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return {"features": FEATURES, "weights": w, "bias": b, "n_train": n}


class MLClassifier:
    def __init__(self, model: dict):
        self.w = model["weights"]
        self.b = model["bias"]
        self.features = model["features"]

    @classmethod
    def load(cls, path: Path = WEIGHTS_PATH) -> "MLClassifier | None":
        try:
            return cls(json.loads(path.read_text()))
        except (OSError, ValueError, KeyError):
            return None

    def predict_proba(self, x: list[float]) -> float:
        return round(_sigmoid(sum(wj * xj for wj, xj in zip(self.w, x)) + self.b), 4)
