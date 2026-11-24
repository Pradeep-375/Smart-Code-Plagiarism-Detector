# Detection algorithms

**Preprocessing** – regex tokenizer per language (Python emits INDENT/DEDENT/NEWLINE), imports/includes/docstrings stripped as boilerplate, then identifiers → `ID`, numbers → `NUM`, strings → `STR`, and operator canonicalisation (`x += 1` → `x = x + 1`). Template/reference code is indexed and excluded from matches.

| Algorithm | What it measures | Resists |
|---|---|---|
| Exact | identical normalised lines | – |
| Token (greedy string tiling) | longest shared token runs (min length 8) | reformatting, comments |
| Lexical | similarity of the raw token stream incl. identifiers | whitespace |
| AST | subtree-hash and sibling-window multisets (Python `ast`; pseudo-AST for brace languages) | renaming, reformatting |
| TF-IDF / cosine | abstracted 3-gram vectors, corpus-wide IDF in batches | reordering of statements |
| Winnowing | rolling-hash k-gram fingerprints (k=7, window 4) | local edits, insertions |
| Structural | per-function control-flow sequences | renaming, expression rewrites |
| Transformation | order-insensitive statement multiset; detects renames, reorders, reformatting | reordering |

**Scoring** – weighted mean with admin-configurable weights (normalised), thresholds medium 50 % / high 75 %. A *confidence* value reflects algorithm agreement and code size (short files are capped at "low"). The optional ML layer (pure-Python logistic regression, `model_weights.json`, trained by `scripts/train_ml.py`) supplies a probability shown alongside, never replacing, the rule-based score.

**Explanations** – e.g. "identifiers renamed (n)", "statements reordered", "formatting-only changes", "long contiguous matches", with matched line ranges in both files.

**Limits** – pairwise cost O(n²) (inverted-index prefilter above 150 submissions); per-file token cap 12 000; very short programs are low-confidence.
