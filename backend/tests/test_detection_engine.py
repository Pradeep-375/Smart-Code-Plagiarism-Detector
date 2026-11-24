"""Unit tests for the plagiarism detection engine (pure Python, no database needed)."""
import pytest

from app.detection_engine import (
    DetectionConfig, ReferenceIndex, TfidfModel, compare_prepared, compare_sources, compare_submissions,
    detect_language, prepare_file,
)
from app.detection_engine.algorithms import greedy_string_tiling, kgram_hashes, winnow
from app.detection_engine.normalizer import canonicalize
from app.detection_engine.samples import (
    JAVA, JAVA_RENAME, PY, PY_RESTRUCTURED, change_comments_python, expand_augassign, reformat_python,
    rename_identifiers, rename_python, reorder_python,
)
from app.detection_engine.tokenizer import tokenize


# ------------------------------------------------------------------ tokenizer / normaliser
def test_tokenizer_strips_comments_and_keeps_strings():
    r = tokenize('x = "a # not comment"  # real comment\n', "python")
    assert [t.text for t in r.tokens if t.kind != "NEWLINE"] == ["x", "=", '"a # not comment"']
    assert r.comments == ["# real comment"]


def test_tokenizer_python_indentation_tokens():
    kinds = [t.kind for t in tokenize("if a:\n    b\nc\n", "python").tokens]
    assert "INDENT" in kinds and "DEDENT" in kinds


def test_tokenizer_c_preprocessor_and_block_comment():
    r = tokenize("#include <stdio.h>\n/* hi */ int x;\n", "c")
    assert r.preprocessor_lines == 1 and r.comments == ["/* hi */"]
    assert [t.text for t in r.tokens] == ["int", "x", ";"]


def test_canonicalize_augmented_assignment_and_increment():
    assert canonicalize(["ID", "+=", "NUM"]) == ["ID", "=", "ID", "+", "NUM"]
    assert canonicalize(["ID", "++"]) == ["ID", "=", "ID", "+", "NUM"]
    assert canonicalize(["ID", "[", "ID", "]", "-=", "NUM"]) == ["ID", "[", "ID", "]", "=", "ID", "[", "ID", "]", "-", "NUM"]


def test_language_detection():
    assert detect_language("a/b/Main.JAVA") == "java"
    assert detect_language("x.cpp") == "cpp"
    assert detect_language("x.rb") is None


# ------------------------------------------------------------------ algorithms
def test_winnowing_guarantee_shared_fingerprint_for_long_match():
    a = [f"s{i}" for i in range(60)]
    b = ["x1", "x2", "x3"] + a[10:40] + ["y1", "y2"]
    k, w = 7, 4
    fa = {h for h, _ in winnow(kgram_hashes(a, k), w)}
    fb = {h for h, _ in winnow(kgram_hashes(b, k), w)}
    assert fa & fb  # match of 30 >= w + k - 1 must be detected


def test_greedy_tiling_handles_block_moves():
    a = list("abcdefghij") * 1 + list("0123456789")
    b = list("0123456789") + list("abcdefghij")
    tiles = greedy_string_tiling(a, b, 5)
    assert sum(t[2] for t in tiles) == 20


# ------------------------------------------------------------------ detection scenarios
SRC = PY["grade_report"]


def pct(a, b, lang="python"):
    return compare_sources(a, b, lang)


def test_identical_code_is_100():
    r = pct(SRC, SRC)
    assert r.overall_pct == 100 and r.identical
    assert all(v == 1.0 for v in r.scores.values())


def test_reformatted_code_is_high():
    r = pct(SRC, reformat_python(SRC))
    assert r.overall_pct >= 85
    assert any(t["type"] == "reformatting" for t in r.transformations)


def test_renamed_variables_detected_and_explained():
    r = pct(SRC, rename_python(SRC))
    assert r.overall_pct >= 80
    assert r.scores["exact"] < 0.6 and r.scores["token"] > 0.9
    kinds = [t["type"] for t in r.transformations]
    assert "identifier_renaming" in kinds
    assert any("renamed" in e.lower() for e in r.explanations)


def test_modified_comments_barely_change_score():
    r = pct(SRC, change_comments_python(SRC))
    assert r.overall_pct >= 90


def test_restructured_code_is_flagged_but_lower_than_identical():
    r = pct(PY["sorting_suite"], PY_RESTRUCTURED["sorting_suite"])
    assert 40 <= r.overall_pct < 100


def test_reordered_functions_detected():
    src = PY["prime_tools"]
    r = pct(src, expand_augassign(reorder_python(src)))
    assert r.overall_pct >= 70
    assert r.scores["transformation"] >= r.scores["token"]


def test_completely_different_programs_are_low():
    r = pct(PY["bank_account"], PY["matrix_ops"])
    assert r.overall_pct < 30 and r.level == "low"


def test_independent_solutions_of_same_task_stay_below_review_threshold():
    r = pct(PY["sorting_suite"], PY["sort_alt"])
    assert r.overall_pct < 40


def test_matched_segments_have_line_numbers_and_point_at_shared_code():
    r = pct(SRC, rename_python(SRC))
    assert r.segments
    seg = r.segments[0]
    assert 1 <= seg.a_start <= seg.a_end and 1 <= seg.b_start <= seg.b_end


def test_scores_are_weighted_and_configurable():
    cfg = DetectionConfig(weights={k: 0.0 for k in DetectionConfig().weights} | {"exact": 1.0})
    a = prepare_file(SRC, "python", "a", cfg)
    b = prepare_file(rename_python(SRC), "python", "b", cfg)
    r = compare_prepared(a, b, cfg)
    assert r.overall == pytest.approx(r.scores["exact"], abs=1e-3)


def test_thresholds_control_level():
    cfg = DetectionConfig(thresholds={"medium": 10.0, "high": 20.0})
    r = compare_sources(PY["bank_account"], PY["matrix_ops"], "python", cfg)
    assert r.level in ("medium", "high")


def test_explanations_always_state_that_similarity_is_not_proof():
    r = pct(SRC, rename_python(SRC))
    assert "not proof" in r.explanations[-1]


def test_syntax_error_files_do_not_crash():
    broken = "def f(:\n    return (\n"
    r = compare_sources(broken, broken, "python")
    assert r.overall_pct == 100


def test_tiny_files_have_low_confidence():
    r = pct("x = 1\n", "x = 1\n")
    assert r.confidence_label == "low"


def test_java_rename_detected():
    src = JAVA["Inventory"]
    r = compare_sources(src, rename_identifiers(src, "java", JAVA_RENAME["Inventory"]), "java")
    assert r.overall_pct >= 75
    assert compare_sources(JAVA["Inventory"], JAVA["ShapeAreas"], "java").overall_pct < 35


# ------------------------------------------------------------------ batch / submission level
def test_tfidf_corpus_downweights_common_boilerplate():
    cfg = DetectionConfig()
    docs = [prepare_file(PY[n], "python", n, cfg) for n in ("bank_account", "matrix_ops", "grade_report", "temperature")]
    model = TfidfModel.fit([d.tf for d in docs])
    r1 = compare_prepared(docs[0], docs[1], cfg, model)
    assert 0 <= r1.scores["tfidf"] <= 1


def test_submission_comparison_multi_file():
    cfg = DetectionConfig()
    a1 = prepare_file(PY["bank_account"], "python", "bank.py", cfg)
    a2 = prepare_file(PY["matrix_ops"], "python", "m.py", cfg)
    b1 = prepare_file(rename_python(PY["bank_account"]), "python", "account.py", cfg)
    b2 = prepare_file(PY["word_stats"], "python", "w.py", cfg)
    res = compare_submissions([a1, a2], [b1, b2], cfg)
    assert 20 < res.overall_pct < 80          # one of two files copied
    assert {fp["a_name"] for fp in res.file_pairs} >= {"bank.py"}
    assert all(seg.a_file in (0, 1) for seg in res.segments)


def test_submissions_in_different_languages_do_not_match():
    cfg = DetectionConfig()
    res = compare_submissions([prepare_file(PY["bank_account"], "python", "a.py", cfg)],
                              [prepare_file(JAVA["Inventory"], "java", "A.java", cfg)], cfg)
    assert res.overall == 0


def test_reference_template_code_is_excluded():
    cfg = DetectionConfig()
    template = PY["matrix_ops"]
    student_a = template + "\n\ndef extra_a(v):\n    return sorted(v)[::-1]\n"
    student_b = template + "\n\ndef other_b(text):\n    return text.upper().split()\n"
    plain = compare_prepared(prepare_file(student_a, "python", "a", cfg), prepare_file(student_b, "python", "b", cfg), cfg)
    ref = ReferenceIndex.build([("tpl.py", "python", template)], cfg)
    masked = compare_prepared(prepare_file(student_a, "python", "a", cfg, ref),
                              prepare_file(student_b, "python", "b", cfg, ref), cfg)
    assert plain.overall_pct > 60
    assert masked.overall_pct < plain.overall_pct - 25


def test_engine_is_deterministic():
    r1 = pct(SRC, rename_python(SRC))
    r2 = pct(SRC, rename_python(SRC))
    assert r1.scores == r2.scores and r1.overall == r2.overall
