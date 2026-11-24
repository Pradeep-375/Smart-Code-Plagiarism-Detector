"""PDF report generation with ReportLab. Functions take plain dictionaries so they are easy to test."""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

PROJECT_TITLE = "Smart Code Plagiarism Detection System"
NAVY = colors.HexColor("#1e1b4b")
INDIGO = colors.HexColor("#4f46e5")
LIGHT = colors.HexColor("#eef2ff")

ALGORITHM_LABELS = {
    "exact": "Exact line matching",
    "token": "Token n-gram similarity",
    "lexical": "Lexical similarity",
    "ast": "Abstract syntax tree",
    "tfidf": "TF-IDF cosine similarity",
    "winnowing": "Winnowing fingerprints",
    "structural": "Structural (function-level)",
    "transformation": "Transformation-resistant",
}

METHODOLOGY = [
    ("Exact matching", "Counts non-trivial source lines that appear verbatim in both files; byte-identical files are flagged as duplicates."),
    ("Token similarity", "Source is tokenised (comments and whitespace removed; identifiers, numbers and strings abstracted) and token 4-grams are compared."),
    ("Lexical similarity", "Compares the token stream with original identifier names, ignoring comments and formatting."),
    ("AST analysis", "Compares parse-tree structure (Python AST; control-structure skeleton for other languages)."),
    ("TF-IDF / cosine", "Token trigrams are weighted by rarity across all submissions and compared with cosine similarity."),
    ("Winnowing", "Hashes of token k-grams are sampled with the winnowing algorithm; shared fingerprints locate matching regions."),
    ("Structural", "Functions are matched one-to-one regardless of order, combined with a control-flow profile."),
    ("Transformation analysis", "Compares a canonical form (functions sorted, names abstracted) to see through renaming and reordering."),
]


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], textColor=NAVY, fontSize=22, spaceAfter=4),
        "sub": ParagraphStyle("s", parent=ss["Normal"], textColor=colors.HexColor("#475569"), alignment=TA_CENTER, fontSize=10),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], textColor=INDIGO, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13),
        "small": ParagraphStyle("sm", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#475569")),
        "code": ParagraphStyle("c", fontName="Courier", fontSize=6.5, leading=8),
        "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.5, leading=11),
    }


def _p(text, style):
    return Paragraph(escape(str(text)), style)


def _table(rows, col_widths=None, header=True):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(15 * mm, 8 * mm, f"{PROJECT_TITLE} - similarity indicators require faculty review and are not proof of plagiarism.")
    canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=16 * mm,
                             title=PROJECT_TITLE, author=PROJECT_TITLE)


def _fmt(dt) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    return str(dt or "-")


def _header(st, subtitle):
    return [_p(PROJECT_TITLE, st["title"]), _p(subtitle, st["sub"]), Spacer(1, 4), HRFlowable(width="100%", color=INDIGO, thickness=1.2), Spacer(1, 8)]


def _snippet(content: str, start: int, end: int, max_lines: int = 40) -> str:
    lines = content.split("\n")
    chunk = lines[max(0, start - 1): end][:max_lines]
    width = len(str(start + len(chunk)))
    return "\n".join(f"{start + i:>{width}} {ln[:58]}" for i, ln in enumerate(chunk))


def build_pair_report(d: dict) -> bytes:
    """``d`` keys: assignment{title,language_key,deadline,description}, generated_at, generated_by,
    student_a, student_b, submission_a{id,submitted_at,files[]}, submission_b, result{overall,scores,confidence,
    confidence_label,risk_level,is_duplicate,explanations,review_status,review_notes,override_score,reviewer,reviewed_at,
    segments[{a_file,b_file,a_start_line,a_end_line,b_start_line,b_end_line,token_count}]}, files_a{name:content}, files_b."""
    st = _styles()
    r = d["result"]
    a = d["assignment"]
    buf = io.BytesIO()
    story = _header(st, "Pairwise Similarity Report")

    story.append(_p("Assignment information", st["h2"]))
    story.append(_table([
        ["Title", _p(a["title"], st["cell"])], ["Language", a["language_key"]], ["Deadline", _fmt(a.get("deadline"))],
        ["Report generated", f"{_fmt(d['generated_at'])} by {d.get('generated_by', '-')}"],
        ["Analysis date", _fmt(d.get("analyzed_at"))],
    ], [40 * mm, 140 * mm], header=False))

    story.append(_p("Submission details", st["h2"]))
    story.append(_table([
        ["", "Submission A", "Submission B"],
        ["Student", _p(d["student_a"], st["cell"]), _p(d["student_b"], st["cell"])],
        ["Submission ID", d["submission_a"]["id"], d["submission_b"]["id"]],
        ["Submitted at", _fmt(d["submission_a"].get("submitted_at")), _fmt(d["submission_b"].get("submitted_at"))],
        ["Files", _p(", ".join(d["submission_a"].get("files", [])), st["cell"]), _p(", ".join(d["submission_b"].get("files", [])), st["cell"])],
    ], [35 * mm, 72 * mm, 73 * mm]))

    story.append(_p("Result summary", st["h2"]))
    effective = r.get("override_score")
    summary = [
        ["Overall similarity", f"{r['overall'] * 100:.1f}%"],
        ["Risk level", r["risk_level"].upper()],
        ["Confidence", f"{r['confidence_label']} ({r['confidence'] * 100:.0f}%)"],
        ["Duplicate files", "Yes" if r.get("is_duplicate") else "No"],
    ]
    if effective is not None:
        summary.append(["Faculty-adjusted similarity", f"{effective * 100:.1f}%"])
    story.append(_table(summary, [60 * mm, 120 * mm], header=False))

    story.append(_p("Algorithm-wise scores", st["h2"]))
    rows = [["Algorithm", "Score"]] + [[ALGORITHM_LABELS.get(k, k), f"{v * 100:.1f}%"] for k, v in r["scores"].items()]
    story.append(_table(rows, [110 * mm, 70 * mm]))

    story.append(_p("Explanation of findings", st["h2"]))
    for line in r.get("explanations", []):
        story.append(_p("- " + line, st["body"]))

    story.append(_p("Faculty review", st["h2"]))
    story.append(_table([
        ["Review status", r["review_status"].capitalize()],
        ["Reviewed by", f"{r.get('reviewer') or '-'}  ({_fmt(r.get('reviewed_at'))})"],
        ["Final assessment notes", _p(r.get("review_notes") or "No notes recorded.", st["cell"])],
    ], [50 * mm, 130 * mm], header=False))
    story.append(Spacer(1, 4))
    story.append(_p("Only faculty review can determine whether academic misconduct occurred. Similarity is not confirmed plagiarism.", st["small"]))

    story.append(PageBreak())
    story.append(_p("Matched code sections (side by side)", st["h2"]))
    segments = r.get("segments", [])
    if not segments:
        story.append(_p("No contiguous matching regions were found.", st["body"]))
    for n, seg in enumerate(segments[:8], start=1):
        ca = d["files_a"].get(seg["a_file"], next(iter(d["files_a"].values()), ""))
        cb = d["files_b"].get(seg["b_file"], next(iter(d["files_b"].values()), ""))
        story.append(_p(f"Match {n}: A {seg['a_file']} lines {seg['a_start_line']}-{seg['a_end_line']}  |  "
                        f"B {seg['b_file']} lines {seg['b_start_line']}-{seg['b_end_line']}  ({seg['token_count']} tokens)", st["small"]))
        pa = Preformatted(_snippet(ca, seg["a_start_line"], seg["a_end_line"]), st["code"])
        pb = Preformatted(_snippet(cb, seg["b_start_line"], seg["b_end_line"]), st["code"])
        t = Table([[pa, pb]], colWidths=[90 * mm, 90 * mm])
        t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, INDIGO), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                               ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story += [t, Spacer(1, 6)]
    if len(segments) > 8:
        story.append(_p(f"{len(segments) - 8} further match(es) omitted from this report.", st["small"]))

    story.append(_p("Detection methodology", st["h2"]))
    for name, text in METHODOLOGY:
        story.append(_p(f"{name}: {text}", st["body"]))

    _doc(buf).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def build_assignment_report(d: dict) -> bytes:
    """``d`` keys: assignment, generated_at, generated_by, stats{submissions,analyzed,pairs,average,flagged,review_threshold},
    rows[{student_a,student_b,overall,risk_level,confidence_label,review_status}]."""
    st = _styles()
    a, s = d["assignment"], d["stats"]
    buf = io.BytesIO()
    story = _header(st, "Assignment Plagiarism Report")
    story.append(_p("Assignment information", st["h2"]))
    story.append(_table([
        ["Title", _p(a["title"], st["cell"])], ["Language", a["language_key"]], ["Deadline", _fmt(a.get("deadline"))],
        ["Report generated", f"{_fmt(d['generated_at'])} by {d.get('generated_by', '-')}"],
    ], [40 * mm, 140 * mm], header=False))
    story.append(_p("Summary", st["h2"]))
    story.append(_table([
        ["Submissions", s["submissions"]], ["Compared pairs", s["pairs"]],
        ["Average similarity", f"{s['average'] * 100:.1f}%"],
        [f"Pairs at/above review threshold ({s['review_threshold'] * 100:.0f}%)", s["flagged"]],
    ], [90 * mm, 90 * mm], header=False))
    story.append(_p("Compared pairs (highest similarity first)", st["h2"]))
    rows = [["Student A", "Student B", "Similarity", "Risk", "Confidence", "Review"]]
    for r in d["rows"][:300]:
        rows.append([_p(r["student_a"], st["cell"]), _p(r["student_b"], st["cell"]), f"{r['overall'] * 100:.1f}%", r["risk_level"], r["confidence_label"], r["review_status"]])
    story.append(_table(rows, [48 * mm, 48 * mm, 22 * mm, 18 * mm, 22 * mm, 22 * mm]))
    story.append(Spacer(1, 6))
    story.append(_p("Similarity scores are indicators for human review, not findings of misconduct.", st["small"]))
    _doc(buf).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
