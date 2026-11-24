"""Configurable weighted scoring, similarity levels and confidence indicators."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

ALGORITHMS = (
    "exact", "token", "lexical", "ast", "tfidf", "winnowing", "structural", "transformation",
)

ALGORITHM_LABELS = {
    "exact": "Exact matching",
    "token": "Token-based (greedy tiling)",
    "lexical": "Lexical similarity",
    "ast": "AST analysis",
    "tfidf": "TF-IDF / cosine",
    "winnowing": "Winnowing fingerprints",
    "structural": "Structural similarity",
    "transformation": "Transformation analysis",
}

DEFAULT_WEIGHTS = {
    "exact": 0.08,
    "token": 0.17,
    "lexical": 0.10,
    "ast": 0.15,
    "tfidf": 0.10,
    "winnowing": 0.18,
    "structural": 0.10,
    "transformation": 0.12,
}

# Percent thresholds: >= high -> "high", >= medium -> "medium", else "low".
DEFAULT_THRESHOLDS = {"medium": 50.0, "high": 75.0}


@dataclass
class DetectionConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    thresholds: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    kgram: int = 7              # winnowing k-gram length (symbols)
    window: int = 4             # winnowing window size
    min_tile: int = 8           # minimum greedy-tiling match length
    tfidf_ngram: int = 3
    min_tokens: int = 25        # below this a comparison is flagged as low-confidence
    max_tokens: int = 12000     # hard cap per file (protects the server from huge inputs)
    seq_cap: int = 2500

    def normalized_weights(self) -> dict[str, float]:
        w = {a: max(0.0, float(self.weights.get(a, 0.0))) for a in ALGORITHMS}
        total = sum(w.values())
        if total <= 0:
            return dict(DEFAULT_WEIGHTS)
        return {a: v / total for a, v in w.items()}

    @classmethod
    def from_dict(cls, data: dict | None) -> "DetectionConfig":
        cfg = cls()
        if not data:
            return cfg
        if "weights" in data and data["weights"]:
            cfg.weights.update({k: float(v) for k, v in data["weights"].items() if k in ALGORITHMS})
        if "thresholds" in data and data["thresholds"]:
            cfg.thresholds.update({k: float(v) for k, v in data["thresholds"].items() if k in ("medium", "high")})
        for key in ("kgram", "window", "min_tile", "min_tokens"):
            if key in data and data[key] is not None:
                setattr(cfg, key, int(data[key]))
        return cfg


def combine(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted mean of algorithm scores (all in 0..1)."""
    return sum(scores.get(a, 0.0) * weights.get(a, 0.0) for a in ALGORITHMS)


def level_for(overall_pct: float, thresholds: dict[str, float]) -> str:
    if overall_pct >= thresholds["high"]:
        return "high"
    if overall_pct >= thresholds["medium"]:
        return "medium"
    return "low"


def confidence(scores: dict[str, float], min_tokens: int, cfg: DetectionConfig) -> tuple[float, str]:
    """Confidence in the *measurement*: do the independent algorithms agree, and is there enough code?"""
    vals = [scores.get(a, 0.0) for a in ALGORITHMS if a != "exact"]
    spread = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    agreement = 1.0 - min(1.0, spread / 0.4)
    size_factor = min(1.0, min_tokens / 120.0)
    value = round(0.6 * agreement + 0.4 * size_factor, 3)
    if min_tokens < cfg.min_tokens:
        value = min(value, 0.35)
    label = "high" if value >= 0.75 else "medium" if value >= 0.5 else "low"
    return value, label
