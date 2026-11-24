"""Service-facing API of the detection engine.

The REST layer works with fractions (0..1) and plain dictionaries; this module adapts the
low-level engine (:mod:`app.detection_engine.engine`) to that convention and adds batch
orchestration (corpus-wide TF-IDF, template exclusion, fingerprint pre-filtering, progress).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Iterator

from .algorithms import TfidfModel
from .engine import (
    ReferenceIndex, SubmissionComparison, compare_submissions, prepare_file, PreparedFile,
)
from .languages import LANGUAGES
from .ml import MLClassifier, feature_vector
from .scoring import ALGORITHMS, DEFAULT_WEIGHTS, DetectionConfig

SUPPORTED_LANGUAGES = list(LANGUAGES)
DISCLAIMER = (
    "Similarity is an automated indicator, not proof of plagiarism. Common algorithms, shared templates "
    "and independent solutions to the same task can produce similar code. A faculty member must review the "
    "matched code and decide; no disciplinary action should rest on this score alone."
)
PREFILTER_ABOVE = 150  # submissions; larger classes only compare pairs that share a fingerprint

_ml = MLClassifier.load()

FileList = list[tuple[str, str]]  # (filename, source text)


@dataclass
class EngineConfig:
    """Fractions (0..1) as stored in the database and exposed by the API."""

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    review_threshold: float = 0.5
    high_threshold: float = 0.75

    @classmethod
    def from_dict(cls, data: dict | None) -> "EngineConfig":
        cfg = cls()
        if data:
            if data.get("weights"):
                cfg.weights.update({k: float(v) for k, v in data["weights"].items() if k in ALGORITHMS})
            if data.get("review_threshold") is not None:
                cfg.review_threshold = float(data["review_threshold"])
            if data.get("high_threshold") is not None:
                cfg.high_threshold = float(data["high_threshold"])
        return cfg

    def to_dict(self) -> dict:
        return {"weights": dict(self.weights), "review_threshold": self.review_threshold,
                "high_threshold": self.high_threshold}

    def to_detection_config(self) -> DetectionConfig:
        return DetectionConfig(
            weights=dict(self.weights),
            thresholds={"medium": self.review_threshold * 100, "high": self.high_threshold * 100},
        )


@dataclass
class EngineResult:
    overall: float
    scores: dict[str, float]
    confidence: float
    confidence_label: str
    risk_level: str
    is_duplicate: bool
    explanations: list[str]
    ml_probability: float | None
    segments: list[dict]
    transformations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall, "scores": self.scores, "confidence": self.confidence,
            "confidence_label": self.confidence_label, "risk_level": self.risk_level,
            "is_duplicate": self.is_duplicate, "explanations": self.explanations,
            "ml_probability": self.ml_probability, "segments": self.segments,
            "transformations": self.transformations,
        }


def _wrap(res: SubmissionComparison, a: list[PreparedFile], b: list[PreparedFile]) -> EngineResult:
    segs = [
        {
            "a_file": a[s.a_file].name, "b_file": b[s.b_file].name,
            "a_start_line": s.a_start, "a_end_line": s.a_end,
            "b_start_line": s.b_start, "b_end_line": s.b_end,
            "token_count": s.tokens, "kind": s.kind, "similarity": s.similarity,
            "description": s.description,
        }
        for s in res.segments
    ]
    prob = None
    if _ml and res.file_pairs:
        best = max(res.file_pairs, key=lambda p: p["overall"])
        t = best["details"]["token"]
        prob = _ml.predict_proba(feature_vector(res.scores, min(t["tokens_a"], t["tokens_b"]),
                                                t["longest_match"], t["tokens_a"] + t["tokens_b"]))
    return EngineResult(
        overall=res.overall, scores=res.scores, confidence=res.confidence, confidence_label=res.confidence_label,
        risk_level="low", is_duplicate=res.identical, explanations=res.explanations, ml_probability=prob,
        segments=segs, transformations=res.transformations,
    )


class DetectionEngine:
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.cfg = self.config.to_detection_config()

    @staticmethod
    def pair_count(n_main: int, n_extra: int = 0) -> int:
        return n_main * (n_main - 1) // 2 + n_main * n_extra

    def _risk(self, overall: float) -> str:
        if overall >= self.config.high_threshold:
            return "high"
        return "medium" if overall >= self.config.review_threshold else "low"

    def _reference(self, template: FileList | None, language: str) -> ReferenceIndex | None:
        if not template:
            return None
        return ReferenceIndex.build([(n, language, t) for n, t in template], self.cfg)

    def _prep(self, files: FileList, language: str, ref: ReferenceIndex | None) -> list[PreparedFile]:
        return [prepare_file(text, language, name, self.cfg, ref) for name, text in files]

    def _finish(self, res: SubmissionComparison, a: list[PreparedFile], b: list[PreparedFile]) -> EngineResult:
        out = _wrap(res, a, b)
        out.risk_level = self._risk(out.overall)
        return out

    def compare_files(self, files_a: FileList, files_b: FileList, language: str,
                      template: FileList | None = None) -> EngineResult:
        ref = self._reference(template, language)
        pa, pb = self._prep(files_a, language, ref), self._prep(files_b, language, ref)
        model = TfidfModel.fit([f.tf for f in pa + pb])
        return self._finish(compare_submissions(pa, pb, self.cfg, model), pa, pb)

    def compare(self, src_a: str, src_b: str, language: str, template: str | None = None) -> EngineResult:
        tpl = [("template", template)] if template else None
        return self.compare_files([("A", src_a)], [("B", src_b)], language, tpl)

    def compare_batch(
        self, main: dict[int, FileList], language: str, template: FileList | None = None,
        progress: Callable[[int, int], None] | None = None, extra: dict[int, FileList] | None = None,
    ) -> Iterator[tuple[int, int, EngineResult]]:
        """Compare every pair inside ``main`` plus every ``main`` x ``extra`` pair (history)."""
        extra = extra or {}
        ref = self._reference(template, language)
        prepared: dict[int, list[PreparedFile]] = {
            sid: self._prep(files, language, ref) for sid, files in {**main, **extra}.items()
        }
        model = TfidfModel.fit([f.tf for fl in prepared.values() for f in fl])
        ids = list(main)
        pairs = list(combinations(ids, 2)) + [(a, b) for a in ids for b in extra]
        total = len(pairs)
        if len(prepared) > PREFILTER_ABOVE:
            index: dict[int, set[int]] = {}
            for sid, fl in prepared.items():
                index[sid] = {h for f in fl for h, _ in f.fingerprints}
            pairs = [(a, b) for a, b in pairs if index[a] & index[b]]
        done = total - len(pairs)
        for a, b in pairs:
            res = compare_submissions(prepared[a], prepared[b], self.cfg, model)
            done += 1
            if progress:
                progress(done, total)
            yield a, b, self._finish(res, prepared[a], prepared[b])
        if progress:
            progress(total, total)
