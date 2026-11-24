# Detection engine evaluation

Held-out labelled pairs: **80** (62 copied variants, 18 independent pairs).

Decision rule: flag for faculty review when overall similarity ≥ **50%** (the default *medium* threshold).

## Confusion matrix and metrics

| | Predicted: flag | Predicted: no flag |
|---|---|---|
| **Actually copied** | TP = 62 | FN = 0 |
| **Independent** | FP = 0 | TN = 18 |

- Precision: **1.000**
- Recall: **1.000**
- F1-score: **1.000**
- False-positive rate: **0.000**

## Per-category similarity

| Category | Pairs | Min | Mean | Max | Flagged |
|---|---|---|---|---|---|
| identical | 11 | 100.0 | 100.0 | 100.0 | 11/11 |
| reformatted | 15 | 92.0 | 95.6 | 100.0 | 15/15 |
| renamed | 11 | 89.4 | 90.5 | 91.3 | 11/11 |
| comments | 11 | 95.0 | 99.1 | 100.0 | 11/11 |
| restructured | 14 | 56.6 | 82.4 | 90.2 | 14/14 |
| hard_negative | 3 | 21.8 | 28.9 | 34.3 | 0/3 |
| different | 15 | 11.9 | 17.8 | 24.0 | 0/15 |

## Threshold sweep

| Threshold | Precision | Recall | F1 | FP rate |
|---|---|---|---|---|
| 30 | 0.969 | 1.000 | 0.984 | 0.111 |
| 35 | 1.000 | 1.000 | 1.000 | 0.000 |
| 40 | 1.000 | 1.000 | 1.000 | 0.000 |
| 45 | 1.000 | 1.000 | 1.000 | 0.000 |
| 50 | 1.000 | 1.000 | 1.000 | 0.000 |
| 55 | 1.000 | 1.000 | 1.000 | 0.000 |
| 60 | 1.000 | 0.984 | 0.992 | 0.000 |
| 70 | 1.000 | 0.952 | 0.975 | 0.000 |

## False positives and false negatives at the default threshold

**False positives** (independent work flagged): none

**False negatives** (copied variants missed): none

**Highest-scoring independent pairs** (closest to being false positives):
- `sorting_suite~sort_alt` → 34.3%
- `prime_tools~prime_alt` → 30.8%
- `temperature~sorting_suite` → 24.0%
- `sorting_suite~temperature` → 23.9%
- `word_stats~sorting_suite` → 23.7%

**Lowest-scoring copied variants** (closest to being missed):
- `prime_tools:hand-restructured` → 56.6%
- `temperature:hand-restructured` → 60.2%
- `sorting_suite:hand-restructured` → 67.0%
- `temperature:reorder+rename` → 82.6%
- `word_stats:reorder+rename` → 84.7%

> Caveat: the evaluation set is small and synthetic (programmatic and hand-made variants of short programs). Use it as a regression benchmark, not as evidence of real-world accuracy; calibrate thresholds on your own course data.
