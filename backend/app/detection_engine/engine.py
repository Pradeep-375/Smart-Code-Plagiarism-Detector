"""Multi-layer plagiarism detection engine.

Typical use::

    cfg = DetectionConfig()
    a = prepare_file(src_a, "python", "a.py", cfg)
    b = prepare_file(src_b, "python", "b.py", cfg)
    result = compare_prepared(a, b, cfg)
    print(result.overall_pct, result.scores)

For batches, prepare every file once and reuse a corpus-wide :class:`TfidfModel`.
The engine only *reads* source text - nothing submitted is ever executed.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .algorithms import (
    TfidfModel, cosine, dice_counter, dice_sets, greedy_string_tiling, kgram_hashes,
    sequence_ratio, stable_hash, top_shared_terms, winnow, winnow_runs,
)
from .languages import get_language
from .normalizer import abstract, canonicalize, split_statements, strip_boilerplate
from .scoring import (
    ALGORITHM_LABELS, ALGORITHMS, DetectionConfig, combine, confidence, level_for,
)
from .structure import FuncInfo, build_trees, count_labels, extract_functions, tree_hashes
from .tokenizer import STRUCT_KINDS, Token, normalize_newlines, tokenize

SEGMENT_PRIORITY = {"exact": 0, "structural": 1, "token": 2, "winnowing": 3}


# =========================================================================== data classes
@dataclass
class PreparedFile:
    name: str
    language: str
    family: str
    source: str
    n_lines: int
    symbols: list[str]
    sym_tokens: list[Token]
    lex: list[str]
    fingerprints: list[tuple[int, int]]
    tf: Counter
    ast_counter: Counter
    functions: list[FuncInfo]
    stmt_counter: Counter
    code_lines: list[tuple[int, str]]        # (line number, whitespace-collapsed text)
    comments: list[str]
    doc_hash: str
    code_hash: str
    label_counts: Counter
    truncated: bool = False

    @property
    def token_count(self) -> int:
        return len(self.symbols)


@dataclass
class ReferenceIndex:
    """Instructor-provided template / starter code that must not count as similarity."""

    kgrams: set[int] = field(default_factory=set)
    statements: set[int] = field(default_factory=set)
    lines: set[str] = field(default_factory=set)
    ast_hashes: set[int] = field(default_factory=set)
    func_seqs: list[list[str]] = field(default_factory=list)
    k: int = 7

    @classmethod
    def build(cls, files: list[tuple[str, str, str]], cfg: DetectionConfig | None = None) -> "ReferenceIndex":
        """``files`` is a list of ``(name, language, source)``."""
        cfg = cfg or DetectionConfig()
        ref = cls(k=cfg.kgram)
        for name, language, source in files:
            try:
                pf = prepare_file(source, language, name, cfg)
            except ValueError:
                continue
            ref.kgrams.update(kgram_hashes(pf.symbols, cfg.kgram))
            ref.statements.update(pf.stmt_counter.keys())
            ref.lines.update(t for _, t in pf.code_lines)
            ref.ast_hashes.update(pf.ast_counter.keys())
            ref.func_seqs.extend(f.seq for f in pf.functions if f.size >= 3)
        return ref


@dataclass
class Segment:
    kind: str
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    tokens: int = 0
    similarity: float = 1.0
    a_file: int = 0
    b_file: int = 0
    description: str = ""


@dataclass
class PairComparison:
    a_name: str
    b_name: str
    scores: dict[str, float]
    overall: float                      # 0..1
    confidence: float
    confidence_label: str
    level: str
    segments: list[Segment]
    transformations: list[dict]
    explanations: list[str]
    details: dict
    min_tokens: int = 0
    identical: bool = False

    @property
    def overall_pct(self) -> float:
        return round(self.overall * 100, 2)


@dataclass
class SubmissionComparison:
    scores: dict[str, float]
    overall: float
    confidence: float
    confidence_label: str
    level: str
    segments: list[Segment]
    transformations: list[dict]
    explanations: list[str]
    file_pairs: list[dict]
    identical: bool = False

    @property
    def overall_pct(self) -> float:
        return round(self.overall * 100, 2)


# =========================================================================== preparation
def _collapse(text: str) -> str:
    return " ".join(text.split())


def prepare_file(
    source: str,
    language: str,
    name: str = "",
    cfg: DetectionConfig | None = None,
    reference: ReferenceIndex | None = None,
) -> PreparedFile:
    cfg = cfg or DetectionConfig()
    spec = get_language(language)
    source = normalize_newlines(source)
    tr = tokenize(source, language)

    # ---- per-line "code" view (comment-only and blank lines are ignored)
    token_lines: set[int] = set()
    for t in tr.tokens:
        if t.kind in STRUCT_KINDS:
            continue
        token_lines.update(range(t.line, t.end_line + 1))
    src_lines = source.split("\n")
    code_lines = [
        (i + 1, _collapse(src_lines[i])) for i in sorted(token_lines) if i < len(src_lines) and src_lines[i].strip()
    ]
    if reference and reference.lines:
        code_lines = [(n, t) for n, t in code_lines if t not in reference.lines]

    doc_hash = hashlib.sha256(
        "\n".join(l.rstrip() for l in src_lines).strip().encode("utf-8", "replace")
    ).hexdigest()
    code_hash = hashlib.sha256("\n".join(t for _, t in code_lines).encode("utf-8", "replace")).hexdigest()

    # ---- boilerplate removal + abstraction
    toks = strip_boilerplate(tr.tokens, spec)
    truncated = False
    if len(toks) > cfg.max_tokens:
        toks = toks[: cfg.max_tokens]
        truncated = True
    symbols = [abstract(t) for t in toks]

    # ---- reference (template) masking
    if reference and reference.kgrams and len(symbols) >= reference.k:
        hs = kgram_hashes(symbols, reference.k)
        covered = bytearray(len(symbols))
        for i, h in enumerate(hs):
            if h in reference.kgrams:
                for p in range(i, i + reference.k):
                    covered[p] = 1
        if any(covered):
            keep = [i for i in range(len(symbols)) if not covered[i]]
            toks = [toks[i] for i in keep]
            symbols = [symbols[i] for i in keep]

    # quote style is formatting, not content: normalise string delimiters for the lexical view
    lex = [("STR:" + t.text.strip("'\"`")) if t.kind == "STRING" else t.text
           for t in toks if t.kind not in STRUCT_KINDS]

    # ---- fingerprints & tf-idf features
    hashes = kgram_hashes(symbols, cfg.kgram)
    fps = winnow(hashes, cfg.window)
    n = cfg.tfidf_ngram
    tf: Counter = Counter(" ".join(symbols[i : i + n]) for i in range(max(0, len(symbols) - n + 1)))

    # ---- trees
    ast_tree, struct_tree = build_trees(source, spec, tr.tokens)
    ast_counter = tree_hashes(ast_tree)
    functions = extract_functions(struct_tree)
    if reference:
        for h in reference.ast_hashes:
            ast_counter.pop(h, None)
        if reference.func_seqs:
            functions = [
                f for f in functions
                if not (f.size >= 3 and any(sequence_ratio(f.seq, r) >= 0.95 for r in reference.func_seqs))
            ]

    # ---- canonical statements (order-insensitive)
    stmt_counter: Counter = Counter()
    for st in split_statements(toks, spec):
        syms = canonicalize([abstract(t) for t in st])
        if len(syms) < 3:
            continue
        stmt_counter[stable_hash(" ".join(syms))] += 1
    if reference:
        for h in reference.statements:
            stmt_counter.pop(h, None)

    return PreparedFile(
        name=name, language=spec.key, family=spec.family, source=source, n_lines=tr.total_lines,
        symbols=symbols, sym_tokens=toks, lex=lex, fingerprints=fps, tf=tf,
        ast_counter=ast_counter, functions=functions, stmt_counter=stmt_counter,
        code_lines=code_lines, comments=tr.comments, doc_hash=doc_hash, code_hash=code_hash,
        label_counts=count_labels(struct_tree), truncated=truncated,
    )


# =========================================================================== helpers
def _lines_for(tokens: list[Token], i: int, length: int) -> tuple[int, int] | None:
    lo, hi = i, i + length - 1
    while lo <= hi and tokens[lo].kind in STRUCT_KINDS:
        lo += 1
    while hi >= lo and tokens[hi].kind in STRUCT_KINDS:
        hi -= 1
    if lo > hi:
        return None
    return tokens[lo].line, max(tokens[hi].end_line, tokens[hi].line)


def _tile_segments(a: PreparedFile, b: PreparedFile, runs: list[tuple[int, int, int]], kind: str) -> list[Segment]:
    segs: list[Segment] = []
    for i, j, length in runs:
        ra = _lines_for(a.sym_tokens, i, length)
        rb = _lines_for(b.sym_tokens, j, length)
        if ra and rb:
            segs.append(Segment(kind, ra[0], ra[1], rb[0], rb[1], tokens=length))
    return segs


def _merge_adjacent(segs: list[Segment], gap: int = 2) -> list[Segment]:
    """Merge neighbouring matches that continue each other in both files."""
    segs = sorted(segs, key=lambda s: (s.a_start, s.b_start))
    out: list[Segment] = []
    for s in segs:
        if out:
            p = out[-1]
            if (
                p.kind == s.kind
                and 0 <= s.a_start - p.a_end <= gap
                and 0 <= s.b_start - p.b_end <= gap
            ):
                p.a_end = max(p.a_end, s.a_end)
                p.b_end = max(p.b_end, s.b_end)
                p.tokens += s.tokens
                continue
        out.append(Segment(s.kind, s.a_start, s.a_end, s.b_start, s.b_end, s.tokens, s.similarity,
                           s.a_file, s.b_file, s.description))
    return out


def _overlap(a1: int, a2: int, b1: int, b2: int) -> float:
    lo, hi = max(a1, b1), min(a2, b2)
    inter = max(0, hi - lo + 1)
    return inter / max(1, min(a2 - a1 + 1, b2 - b1 + 1))


def consolidate_segments(segs: list[Segment], limit: int = 60) -> list[Segment]:
    segs = sorted(segs, key=lambda s: (SEGMENT_PRIORITY.get(s.kind, 9), -(s.a_end - s.a_start)))
    kept: list[Segment] = []
    for s in segs:
        dup = any(
            _overlap(s.a_start, s.a_end, k.a_start, k.a_end) >= 0.8
            and _overlap(s.b_start, s.b_end, k.b_start, k.b_end) >= 0.8
            for k in kept
        )
        if not dup:
            kept.append(s)
    kept.sort(key=lambda s: (s.a_start, s.b_start))
    return kept[:limit]


# =========================================================================== per-algorithm scorers
def _exact(a: PreparedFile, b: PreparedFile) -> tuple[float, list[Segment], bool, dict]:
    identical = a.doc_hash == b.doc_hash
    if a.code_hash == b.code_hash and a.code_lines:
        n = len(a.code_lines)
        seg = [Segment("exact", a.code_lines[0][0], a.code_lines[-1][0], b.code_lines[0][0],
                       b.code_lines[-1][0], tokens=a.token_count)]
        return 1.0, seg, identical, {"identical_lines": n, "identical_code": True}
    ta = [t for _, t in a.code_lines]
    tb = [t for _, t in b.code_lines]
    sm = SequenceMatcher(None, ta, tb, autojunk=False)
    matched = 0
    segs: list[Segment] = []
    for blk in sm.get_matching_blocks():
        if blk.size == 0:
            continue
        sig = sum(1 for t in ta[blk.a : blk.a + blk.size] if len(t) >= 6)
        matched += sig
        if blk.size >= 3 and sig >= 2:
            la = a.code_lines[blk.a][0], a.code_lines[blk.a + blk.size - 1][0]
            lb = b.code_lines[blk.b][0], b.code_lines[blk.b + blk.size - 1][0]
            segs.append(Segment("exact", la[0], la[1], lb[0], lb[1], tokens=0))
    sig_a = sum(1 for t in ta if len(t) >= 6)
    sig_b = sum(1 for t in tb if len(t) >= 6)
    score = 2.0 * matched / (sig_a + sig_b) if (sig_a + sig_b) else 0.0
    return min(1.0, score), segs, identical, {"identical_lines": matched, "identical_code": False}


def _identifier_mapping(a: PreparedFile, b: PreparedFile, tiles: list[tuple[int, int, int]]) -> dict:
    pairs: Counter = Counter()
    for i, j, length in tiles:
        for t in range(length):
            ta, tb = a.sym_tokens[i + t], b.sym_tokens[j + t]
            if ta.kind == "IDENT" and tb.kind == "IDENT":
                pairs[(ta.text, tb.text)] += 1
    total = sum(pairs.values())
    if total == 0:
        return {"total": 0, "differing": 0, "consistency": 0.0, "examples": []}
    differing = sum(c for (x, y), c in pairs.items() if x != y)
    by_a: dict[str, Counter] = {}
    for (x, y), c in pairs.items():
        by_a.setdefault(x, Counter())[y] += c
    explained = 0
    examples: list[tuple[str, str]] = []
    for x, cnt in by_a.items():
        y, c = cnt.most_common(1)[0]
        if x != y:
            explained += c
            examples.append((x, y))
    consistency = explained / differing if differing else 1.0
    return {
        "total": total, "differing": differing, "consistency": round(consistency, 3),
        "examples": sorted(examples)[:8], "ratio": round(differing / total, 3),
    }


def _comment_similarity(a: PreparedFile, b: PreparedFile) -> float | None:
    wa = {w.lower() for c in a.comments for w in c.split() if w.isalpha()}
    wb = {w.lower() for c in b.comments for w in c.split() if w.isalpha()}
    if not wa and not wb:
        return None
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _structural(a: PreparedFile, b: PreparedFile) -> tuple[float, list[Segment], dict]:
    fa = [f for f in a.functions if f.size >= 3]
    fb = [f for f in b.functions if f.size >= 3]
    if not fa or not fb:
        return 0.0, [], {"functions_a": len(a.functions), "functions_b": len(b.functions), "matched_functions": 0}

    best_a: list[tuple[float, FuncInfo, FuncInfo]] = []
    best_b: dict[int, tuple[float, FuncInfo]] = {}
    for f in fa:
        best = (0.0, fb[0])
        for g in fb:
            r = sequence_ratio(f.seq, g.seq)
            if r > best[0]:
                best = (r, g)
            cur = best_b.get(id(g))
            if cur is None or r > cur[0]:
                best_b[id(g)] = (r, f)
        best_a.append((best[0], f, best[1]))

    wa = sum(f.size for f in fa)
    wb = sum(g.size for g in fb)
    sa = sum(r * f.size for r, f, _ in best_a) / wa
    sb = sum(best_b[id(g)][0] * g.size for g in fb) / wb
    segs: list[Segment] = []
    matched = 0
    for r, f, g in best_a:
        if r >= 0.85 and f.size >= 4 and f.name != "<module>" and g.name != "<module>":
            matched += 1
            segs.append(Segment("structural", f.line, f.end_line, g.line, g.end_line,
                                tokens=f.size, similarity=round(r, 3),
                                description=f"Function '{f.name}' mirrors '{g.name}' ({round(r*100)}% same control-flow)"))
    return (sa + sb) / 2.0, segs, {
        "functions_a": len(a.functions), "functions_b": len(b.functions), "matched_functions": matched,
        "loops_a": sum(a.label_counts[k] for k in ("FOR", "WHILE", "DO")),
        "loops_b": sum(b.label_counts[k] for k in ("FOR", "WHILE", "DO")),
        "conditions_a": sum(a.label_counts[k] for k in ("IF", "ELIF", "SWITCH")),
        "conditions_b": sum(b.label_counts[k] for k in ("IF", "ELIF", "SWITCH")),
    }


# =========================================================================== pair comparison
def compare_prepared(
    a: PreparedFile, b: PreparedFile, cfg: DetectionConfig | None = None, tfidf: TfidfModel | None = None
) -> PairComparison:
    cfg = cfg or DetectionConfig()
    scores: dict[str, float] = {}
    details: dict = {}
    segments: list[Segment] = []

    # A. exact
    scores["exact"], seg, identical, d = _exact(a, b)
    segments += seg
    details["exact"] = d

    # B. token-based (greedy string tiling on abstracted tokens)
    tiles = greedy_string_tiling(a.symbols, b.symbols, cfg.min_tile)
    covered = sum(t[2] for t in tiles)
    total = len(a.symbols) + len(b.symbols)
    scores["token"] = (2.0 * covered / total) if total else 0.0
    tile_segs = _merge_adjacent(_tile_segments(a, b, tiles, "token"))
    segments += tile_segs
    longest = max((t[2] for t in tiles), default=0)
    details["token"] = {"tiles": len(tiles), "matched_tokens": covered, "longest_match": longest,
                        "tokens_a": len(a.symbols), "tokens_b": len(b.symbols)}

    # C. lexical (identifier names and literals kept; whitespace/comments gone)
    if a.lex and b.lex:
        scores["lexical"] = sequence_ratio(a.lex, b.lex, cfg.seq_cap)
    else:
        scores["lexical"] = 0.0

    # D. AST
    scores["ast"] = dice_counter(a.ast_counter, b.ast_counter)

    # E. TF-IDF
    model = tfidf or TfidfModel.fit([a.tf, b.tf])
    va, vb = model.vector(a.tf), model.vector(b.tf)
    scores["tfidf"] = cosine(va, vb)
    details["tfidf"] = {"top_shared_ngrams": top_shared_terms(va, vb)}

    # F. winnowing
    set_a = {h for h, _ in a.fingerprints}
    set_b = {h for h, _ in b.fingerprints}
    shared = set_a & set_b
    scores["winnowing"] = dice_sets(set_a, set_b)
    runs = winnow_runs(a.fingerprints, b.fingerprints, cfg.kgram)
    segments += _merge_adjacent(_tile_segments(a, b, runs, "winnowing"))
    details["winnowing"] = {
        "fingerprints_a": len(set_a), "fingerprints_b": len(set_b), "shared": len(shared),
        "containment_a": round(len(shared) / len(set_a), 3) if set_a else 0.0,
        "containment_b": round(len(shared) / len(set_b), 3) if set_b else 0.0,
    }

    # G. structural
    scores["structural"], seg, details["structural"] = _structural(a, b)
    segments += seg

    # H. transformation analysis (identifier/format/comment/order invariant)
    scores["transformation"] = dice_counter(a.stmt_counter, b.stmt_counter)
    mapping = _identifier_mapping(a, b, tiles)
    details["identifiers"] = mapping

    transformations = _detect_transformations(a, b, scores, mapping)
    details["transformations"] = [t["type"] for t in transformations]

    # ---- combine
    weights = cfg.normalized_weights()
    overall = combine(scores, weights)
    if identical:
        overall = 1.0
        scores = {k: 1.0 for k in scores}
    min_tokens = min(a.token_count, b.token_count)
    conf, conf_label = confidence(scores, min_tokens, cfg)
    pct = overall * 100
    level = level_for(pct, cfg.thresholds)
    segments = consolidate_segments(segments)
    explanations = explain(a, b, scores, details, transformations, overall, level, min_tokens, cfg)

    return PairComparison(
        a_name=a.name, b_name=b.name, scores={k: round(v, 4) for k, v in scores.items()},
        overall=round(overall, 4), confidence=conf, confidence_label=conf_label, level=level,
        segments=segments, transformations=transformations, explanations=explanations,
        details=details, min_tokens=min_tokens, identical=identical,
    )


def _detect_transformations(a: PreparedFile, b: PreparedFile, s: dict[str, float], mapping: dict) -> list[dict]:
    out: list[dict] = []
    if mapping.get("differing", 0) >= 3 and mapping.get("ratio", 0) >= 0.15 and mapping.get("consistency", 0) >= 0.8 \
            and s["token"] >= 0.5:
        ex = ", ".join(f"{x}→{y}" for x, y in mapping["examples"][:5])
        out.append({"type": "identifier_renaming", "confidence": mapping["consistency"],
                    "detail": f"Identifiers were renamed consistently across matching code (e.g. {ex})."})
    if s["lexical"] >= 0.85 and s["exact"] <= s["lexical"] - 0.1 and s["token"] >= 0.8:
        out.append({"type": "reformatting", "confidence": round(s["lexical"], 2),
                    "detail": "Code is lexically near-identical but line layout / whitespace differs."})
    cs = _comment_similarity(a, b)
    if s["token"] >= 0.75 and ((a.comments or b.comments) and (cs is not None and cs <= 0.5)):
        out.append({"type": "comment_changes", "confidence": round(s["token"], 2),
                    "detail": "Comments differ (or were added/removed) while the executable code matches."})
    if s["transformation"] >= 0.75 and s["token"] <= s["transformation"] - 0.12:
        out.append({"type": "reordering", "confidence": round(s["transformation"] - s["token"], 2),
                    "detail": "Statements or functions appear in a different order but the same building blocks are present."})
    if s["structural"] >= 0.8 and s["lexical"] <= 0.6 and s["token"] <= 0.75:
        out.append({"type": "restructuring", "confidence": round(s["structural"], 2),
                    "detail": "Control-flow structure matches although the surface code was rewritten."})
    return out


def explain(
    a: PreparedFile, b: PreparedFile, s: dict[str, float], d: dict, transformations: list[dict],
    overall: float, level: str, min_tokens: int, cfg: DetectionConfig,
) -> list[str]:
    pct = lambda v: f"{round(v * 100):d}%"  # noqa: E731
    ex: list[str] = []
    ex.append(
        f"Overall similarity is {pct(overall)} ({level} band; thresholds: medium ≥ {cfg.thresholds['medium']:g}%, "
        f"high ≥ {cfg.thresholds['high']:g}%)."
    )
    if min_tokens < cfg.min_tokens:
        ex.append(f"Very little code to compare ({min_tokens} tokens); short programs often look alike by chance, so confidence is low.")
    if d["exact"].get("identical_code"):
        ex.append("The code is identical line-for-line (ignoring comments and blank lines).")
    elif d["exact"]["identical_lines"]:
        ex.append(f"{d['exact']['identical_lines']} significant lines are textually identical.")
    t = d["token"]
    ex.append(
        f"Token matching: {t['matched_tokens']} of {t['tokens_a']}/{t['tokens_b']} abstracted tokens fall into "
        f"{t['tiles']} shared block(s) of ≥ {cfg.min_tile} tokens (longest {t['longest_match']}) → {pct(s['token'])}."
    )
    w = d["winnowing"]
    ex.append(
        f"Winnowing: {w['shared']} shared fingerprints out of {w['fingerprints_a']} / {w['fingerprints_b']} "
        f"(containment {pct(w['containment_a'])} / {pct(w['containment_b'])}) → {pct(s['winnowing'])}."
    )
    if max(w["containment_a"], w["containment_b"]) - s["winnowing"] >= 0.25 and max(w["containment_a"], w["containment_b"]) >= 0.6:
        small = a.name if w["containment_a"] > w["containment_b"] else b.name
        ex.append(f"Most of '{small}' is contained in the other submission, which may indicate partial copying.")
    ex.append(f"AST: {pct(s['ast'])} of syntax-tree fragments are shared; structure: {pct(s['structural'])}.")
    ex.append(f"Lexical similarity (names and literals preserved): {pct(s['lexical'])}; TF-IDF cosine: {pct(s['tfidf'])}.")
    for tr in transformations:
        ex.append(f"Transformation detected – {tr['type'].replace('_', ' ')}: {tr['detail']}")
    ex.append("Similarity is evidence for review, not proof of plagiarism; a faculty member must review the code before any decision.")
    return ex


# =========================================================================== submission-level comparison
def compare_submissions(
    files_a: list[PreparedFile], files_b: list[PreparedFile], cfg: DetectionConfig | None = None,
    tfidf: TfidfModel | None = None,
) -> SubmissionComparison:
    cfg = cfg or DetectionConfig()
    pairs: dict[tuple[int, int], PairComparison] = {}
    for ia, fa in enumerate(files_a):
        for ib, fb in enumerate(files_b):
            if fa.family == fb.family:
                pairs[(ia, ib)] = compare_prepared(fa, fb, cfg, tfidf)

    if not files_a or not files_b or not pairs:
        zero = {k: 0.0 for k in ALGORITHMS}
        return SubmissionComparison(zero, 0.0, 0.0, "low", "low", [], [],
                                    ["No comparable files (different languages or empty submission)."], [])

    def directional(side: int) -> tuple[dict[str, float], float, list[tuple[int, int]], float]:
        files = files_a if side == 0 else files_b
        weights = [max(1, f.token_count) for f in files]
        total_w = sum(weights)
        agg = {k: 0.0 for k in ALGORITHMS}
        ov = 0.0
        chosen: list[tuple[int, int]] = []
        conf = 0.0
        for idx, w in enumerate(weights):
            cands = [(k, p) for k, p in pairs.items() if k[side] == idx]
            if not cands:
                continue
            key, best = max(cands, key=lambda kp: kp[1].overall)
            chosen.append(key)
            for alg in ALGORITHMS:
                agg[alg] += best.scores[alg] * w / total_w
            ov += best.overall * w / total_w
            conf += best.confidence * w / total_w
        return agg, ov, chosen, conf

    agg_a, ov_a, ch_a, conf_a = directional(0)
    agg_b, ov_b, ch_b, conf_b = directional(1)
    scores = {k: round((agg_a[k] + agg_b[k]) / 2, 4) for k in ALGORITHMS}
    overall = round((ov_a + ov_b) / 2, 4)
    chosen = sorted(set(ch_a) | set(ch_b))
    identical = bool(chosen) and all(pairs[k].identical for k in chosen) and len(files_a) == len(files_b)
    if identical:
        overall = 1.0

    segments: list[Segment] = []
    transformations: list[dict] = []
    file_pairs: list[dict] = []
    for key in chosen:
        pc = pairs[key]
        for sgm in pc.segments:
            segments.append(Segment(sgm.kind, sgm.a_start, sgm.a_end, sgm.b_start, sgm.b_end, sgm.tokens,
                                    sgm.similarity, key[0], key[1], sgm.description))
        for tr in pc.transformations:
            if tr["type"] not in {t["type"] for t in transformations}:
                transformations.append(tr)
        file_pairs.append({
            "a_index": key[0], "b_index": key[1], "a_name": pc.a_name, "b_name": pc.b_name,
            "overall": pc.overall, "scores": pc.scores, "level": pc.level,
            "details": pc.details,
        })
    min_tokens = min(min(f.token_count for f in files_a), min(f.token_count for f in files_b))
    conf, conf_label = (round((conf_a + conf_b) / 2, 3), None)
    conf_label = "high" if conf >= 0.75 else "medium" if conf >= 0.5 else "low"
    level = level_for(overall * 100, cfg.thresholds)
    # explanations from the single best file pair (most informative); mention the rest
    best_key = max(chosen, key=lambda k: pairs[k].overall)
    explanations = list(pairs[best_key].explanations)
    if len(chosen) > 1:
        explanations.insert(1, f"Submission-level score aggregates {len(chosen)} matched file pair(s), weighted by file size.")
    return SubmissionComparison(
        scores=scores, overall=overall, confidence=conf, confidence_label=conf_label, level=level,
        segments=consolidate_segments(segments, limit=120), transformations=transformations,
        explanations=explanations, file_pairs=file_pairs, identical=identical,
    )


def compare_sources(
    src_a: str, src_b: str, language: str, cfg: DetectionConfig | None = None, language_b: str | None = None
) -> PairComparison:
    """Convenience wrapper for comparing two source strings."""
    cfg = cfg or DetectionConfig()
    a = prepare_file(src_a, language, "A", cfg)
    b = prepare_file(src_b, language_b or language, "B", cfg)
    return compare_prepared(a, b, cfg)
