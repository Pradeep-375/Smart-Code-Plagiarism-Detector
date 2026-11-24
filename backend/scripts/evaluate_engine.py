"""Evaluate the detection engine on the labelled sample pairs.

Usage (from ``backend/``)::

    python scripts/evaluate_engine.py                 # prints a report
    python scripts/evaluate_engine.py --write ../docs/evaluation_report.md
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.detection_engine import DetectionConfig, compare_prepared, prepare_file  # noqa: E402
from app.detection_engine.samples import LabelledPair, build_eval_pairs  # noqa: E402


def score_pairs(pairs: list[LabelledPair], cfg: DetectionConfig) -> list[tuple[LabelledPair, float]]:
    out = []
    for p in pairs:
        a = prepare_file(p.a, p.language, "A", cfg)
        b = prepare_file(p.b, p.language, "B", cfg)
        out.append((p, compare_prepared(a, b, cfg).overall * 100))
    return out


def metrics(scored: list[tuple[LabelledPair, float]], threshold: float) -> dict:
    tp = sum(1 for p, s in scored if p.label == 1 and s >= threshold)
    fp = sum(1 for p, s in scored if p.label == 0 and s >= threshold)
    fn = sum(1 for p, s in scored if p.label == 1 and s < threshold)
    tn = sum(1 for p, s in scored if p.label == 0 and s < threshold)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1, "fpr": fpr}


def report(cfg: DetectionConfig | None = None) -> tuple[str, dict]:
    cfg = cfg or DetectionConfig()
    scored = score_pairs(build_eval_pairs(), cfg)
    thr = cfg.thresholds["medium"]
    main = metrics(scored, thr)
    lines: list[str] = []
    lines.append("# Detection engine evaluation\n")
    lines.append(f"Held-out labelled pairs: **{len(scored)}** "
                 f"({sum(1 for p, _ in scored if p.label)} copied variants, "
                 f"{sum(1 for p, _ in scored if not p.label)} independent pairs).\n")
    lines.append(f"Decision rule: flag for faculty review when overall similarity ≥ **{thr:g}%** "
                 f"(the default *medium* threshold).\n")
    lines.append("## Confusion matrix and metrics\n")
    lines.append("| | Predicted: flag | Predicted: no flag |\n|---|---|---|")
    lines.append(f"| **Actually copied** | TP = {main['tp']} | FN = {main['fn']} |")
    lines.append(f"| **Independent** | FP = {main['fp']} | TN = {main['tn']} |\n")
    lines.append(f"- Precision: **{main['precision']:.3f}**\n- Recall: **{main['recall']:.3f}**\n"
                 f"- F1-score: **{main['f1']:.3f}**\n- False-positive rate: **{main['fpr']:.3f}**\n")

    lines.append("## Per-category similarity\n")
    lines.append("| Category | Pairs | Min | Mean | Max | Flagged |\n|---|---|---|---|---|---|")
    cats: dict[str, list[float]] = defaultdict(list)
    for p, s in scored:
        cats[p.category].append(s)
    order = ["identical", "reformatted", "renamed", "comments", "restructured", "hard_negative", "different"]
    for c in order:
        v = cats.get(c, [])
        if not v:
            continue
        flagged = sum(1 for x in v if x >= thr)
        lines.append(f"| {c} | {len(v)} | {min(v):.1f} | {sum(v)/len(v):.1f} | {max(v):.1f} | {flagged}/{len(v)} |")

    lines.append("\n## Threshold sweep\n")
    lines.append("| Threshold | Precision | Recall | F1 | FP rate |\n|---|---|---|---|---|")
    for t in (30, 35, 40, 45, 50, 55, 60, 70):
        m = metrics(scored, t)
        lines.append(f"| {t} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['fpr']:.3f} |")

    lines.append("\n## False positives and false negatives at the default threshold\n")
    fps = [(p, s) for p, s in scored if p.label == 0 and s >= thr]
    fns = [(p, s) for p, s in scored if p.label == 1 and s < thr]
    lines.append("**False positives** (independent work flagged):" + (" none" if not fps else ""))
    for p, s in fps:
        lines.append(f"- `{p.name}` ({p.category}) → {s:.1f}%")
    lines.append("\n**False negatives** (copied variants missed):" + (" none" if not fns else ""))
    for p, s in fns:
        lines.append(f"- `{p.name}` ({p.category}) → {s:.1f}%")
    top_neg = sorted([(s, p.name) for p, s in scored if p.label == 0], reverse=True)[:5]
    lines.append("\n**Highest-scoring independent pairs** (closest to being false positives):")
    for s, n in top_neg:
        lines.append(f"- `{n}` → {s:.1f}%")
    low_pos = sorted([(s, p.name) for p, s in scored if p.label == 1])[:5]
    lines.append("\n**Lowest-scoring copied variants** (closest to being missed):")
    for s, n in low_pos:
        lines.append(f"- `{n}` → {s:.1f}%")
    lines.append(
        "\n> Caveat: the evaluation set is small and synthetic (programmatic and hand-made variants of short "
        "programs). Use it as a regression benchmark, not as evidence of real-world accuracy; calibrate "
        "thresholds on your own course data.\n"
    )
    return "\n".join(lines), main


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", help="write the markdown report to this path")
    args = ap.parse_args()
    text, _ = report()
    print(text)
    if args.write:
        Path(args.write).write_text(text, encoding="utf-8")
        print(f"\nReport written to {args.write}")
