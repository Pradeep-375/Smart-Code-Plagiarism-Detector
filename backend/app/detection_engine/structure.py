"""Syntax-tree construction and structural features.

* Python sources use the real ``ast`` module (fine-grained tree for AST analysis and a
  coarse statement tree for structural analysis).  If the file does not parse, an
  indentation-based pseudo parser is used.
* Other languages use a pseudo-AST built from bracket nesting and statement shapes.
"""
from __future__ import annotations

import ast
import hashlib
from collections import Counter
from dataclasses import dataclass, field

from .languages import LanguageSpec
from .tokenizer import Token

CONTROL_LABELS = {
    "if": "IF", "elif": "ELIF", "for": "FOR", "while": "WHILE", "do": "DO", "switch": "SWITCH",
    "try": "TRY", "catch": "CATCH", "except": "CATCH", "finally": "FINALLY", "with": "WITH",
    "synchronized": "SYNC",
}
LOOP_LABELS = frozenset({"FOR", "WHILE", "DO"})
COND_LABELS = frozenset({"IF", "ELIF", "SWITCH"})
_ASSIGN_OPS = frozenset(
    {"=", "+=", "-=", "*=", "/=", "%=", "//=", "**=", "&=", "|=", "^=", "<<=", ">>=", "++", "--", ":="}
)


@dataclass
class Node:
    label: str
    children: list["Node"] = field(default_factory=list)
    line: int = 0
    end_line: int = 0
    name: str = ""


@dataclass
class FuncInfo:
    name: str
    seq: list[str]
    size: int
    line: int
    end_line: int


def _h(obj: object) -> int:
    return int.from_bytes(hashlib.blake2b(repr(obj).encode(), digest_size=8).digest(), "big")


# --------------------------------------------------------------------------- Python (ast)
def _is_docstring(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _py_fine(node: ast.AST) -> Node:
    label = "Const" if isinstance(node, ast.Constant) else type(node).__name__
    children: list[Node] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.Load, ast.Store, ast.Del, ast.Import, ast.ImportFrom)):
            continue
        if _is_docstring(child):
            continue
        children.append(_py_fine(child))
    return Node(label, children, getattr(node, "lineno", 0), getattr(node, "end_lineno", 0) or 0)


def _py_coarse_block(body: list[ast.stmt]) -> list[Node]:
    out: list[Node] = []
    for st in body:
        if isinstance(st, (ast.Import, ast.ImportFrom, ast.Pass, ast.Global, ast.Nonlocal)):
            continue
        if _is_docstring(st):
            continue
        out.extend(_py_coarse_stmt(st))
    return out


def _span(st: ast.stmt) -> tuple[int, int]:
    return st.lineno, getattr(st, "end_lineno", st.lineno) or st.lineno


def _py_coarse_stmt(st: ast.stmt) -> list[Node]:
    a, b = _span(st)
    if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return [Node("FUNC", _py_coarse_block(st.body), a, b, st.name)]
    if isinstance(st, ast.ClassDef):
        return [Node("CLASS", _py_coarse_block(st.body), a, b, st.name)]
    if isinstance(st, ast.If):
        return _py_if_chain(st, "IF")
    if isinstance(st, (ast.For, ast.AsyncFor)):
        nodes = [Node("FOR", _py_coarse_block(st.body), a, b)]
        if st.orelse:
            nodes.append(Node("ELSE", _py_coarse_block(st.orelse), a, b))
        return nodes
    if isinstance(st, ast.While):
        nodes = [Node("WHILE", _py_coarse_block(st.body), a, b)]
        if st.orelse:
            nodes.append(Node("ELSE", _py_coarse_block(st.orelse), a, b))
        return nodes
    if isinstance(st, ast.Try):
        nodes = [Node("TRY", _py_coarse_block(st.body), a, b)]
        for h in st.handlers:
            nodes.append(Node("CATCH", _py_coarse_block(h.body), a, b))
        if st.orelse:
            nodes.append(Node("ELSE", _py_coarse_block(st.orelse), a, b))
        if st.finalbody:
            nodes.append(Node("FINALLY", _py_coarse_block(st.finalbody), a, b))
        return nodes
    if isinstance(st, (ast.With, ast.AsyncWith)):
        return [Node("WITH", _py_coarse_block(st.body), a, b)]
    if isinstance(st, ast.Return):
        return [Node("RET", [], a, b)]
    if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return [Node("ASG", [], a, b)]
    if isinstance(st, ast.Expr):
        return [Node("CALL" if isinstance(st.value, ast.Call) else "EXPR", [], a, b)]
    if isinstance(st, ast.Break):
        return [Node("BRK", [], a, b)]
    if isinstance(st, ast.Continue):
        return [Node("CONT", [], a, b)]
    if isinstance(st, ast.Raise):
        return [Node("THROW", [], a, b)]
    if isinstance(st, ast.Assert):
        return [Node("CALL", [], a, b)]
    return [Node("EXPR", [], a, b)]


def _py_if_chain(st: ast.If, label: str) -> list[Node]:
    a, b = _span(st)
    nodes = [Node(label, _py_coarse_block(st.body), a, b)]
    if st.orelse:
        if len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
            nodes.extend(_py_if_chain(st.orelse[0], "ELIF"))
        else:
            nodes.append(Node("ELSE", _py_coarse_block(st.orelse), a, b))
    return nodes


# --------------------------------------------------------------------------- pseudo parsers
_TYPE_KEYWORDS = ("class", "struct", "interface", "enum", "namespace", "union", "record")


def classify_leaf(toks: list[Token]) -> Node:
    texts = [t.text for t in toks]
    line, end = toks[0].line, toks[-1].end_line
    first = texts[0]
    if first in ("return",):
        return Node("RET", [], line, end)
    if first in ("break",):
        return Node("BRK", [], line, end)
    if first in ("continue",):
        return Node("CONT", [], line, end)
    if first in ("throw", "raise"):
        return Node("THROW", [], line, end)
    if first == "else":
        return Node("ELIF" if len(texts) > 1 and texts[1] == "if" else "ELSE", [], line, end)
    if first in CONTROL_LABELS and toks[0].kind == "KEYWORD":
        return Node(CONTROL_LABELS[first], [], line, end)
    depth = 0
    for t in toks:
        if t.text in ("(", "["):
            depth += 1
        elif t.text in (")", "]"):
            depth -= 1
        elif depth == 0 and t.kind == "OP" and t.text in _ASSIGN_OPS:
            return Node("ASG", [], line, end)
    if "(" in texts:
        return Node("CALL", [], line, end)
    if len(toks) >= 2 and toks[0].kind in ("KEYWORD", "IDENT"):
        return Node("DECL", [], line, end)
    return Node("EXPR", [], line, end)


def classify_header(toks: list[Token]) -> Node:
    texts = [t.text for t in toks]
    line, end = toks[0].line, toks[-1].end_line
    first = texts[0]
    if first == "else":
        return Node("ELIF" if len(texts) > 1 and texts[1] == "if" else "ELSE", [], line, end)
    if first in CONTROL_LABELS and toks[0].kind == "KEYWORD":
        return Node(CONTROL_LABELS[first], [], line, end)
    if first == "def":
        return Node("FUNC", [], line, end, texts[1] if len(texts) > 1 else "")
    if first == "class" or any(t.text in _TYPE_KEYWORDS for t in toks[:3] if t.kind == "KEYWORD"):
        return Node("CLASS", [], line, end)
    if "function" in texts or "=>" in texts:
        return Node("FUNC", [], line, end)
    if "(" in texts:
        idx = texts.index("(")
        if idx > 0 and toks[idx - 1].kind in ("IDENT", "KEYWORD"):
            return Node("FUNC", [], line, end, texts[idx - 1])
    return Node("BLOCK", [], line, end)


def _fix_end(node: Node) -> int:
    end = node.end_line
    for c in node.children:
        end = max(end, _fix_end(c))
    node.end_line = end
    return end


def parse_brace(tokens: list[Token]) -> Node:
    root = Node("MODULE", [], 1, 1)
    stack = [root]
    cur: list[Token] = []
    paren = 0

    def flush() -> None:
        nonlocal cur
        if cur:
            stack[-1].children.append(classify_leaf(cur))
        cur = []

    for t in tokens:
        if t.kind == "OP":
            if t.text in ("(", "["):
                paren += 1
            elif t.text in (")", "]"):
                paren = max(0, paren - 1)
            elif t.text == "{" and paren == 0:
                node = classify_header(cur) if cur else Node("BLOCK", [], t.line, t.line)
                cur = []
                stack[-1].children.append(node)
                stack.append(node)
                continue
            elif t.text == "}" and paren == 0:
                flush()
                if len(stack) > 1:
                    n = stack.pop()
                    n.end_line = max(n.end_line, t.line)
                continue
            elif t.text == ";" and paren == 0:
                flush()
                continue
        cur.append(t)
    flush()
    _fix_end(root)
    return root


def parse_indent(tokens: list[Token]) -> Node:
    root = Node("MODULE", [], 1, 1)
    stack = [root]
    cur: list[Token] = []
    pending: Node | None = None
    for t in tokens:
        if t.kind == "NEWLINE":
            if cur:
                if cur[-1].text == ":" and cur[0].kind == "KEYWORD" and (
                    cur[0].text in CONTROL_LABELS or cur[0].text in ("def", "class", "else")
                ):
                    node = classify_header(cur)
                    stack[-1].children.append(node)
                    pending = node
                else:
                    stack[-1].children.append(classify_leaf(cur))
                    pending = None
            cur = []
        elif t.kind == "INDENT":
            if pending is None:
                pending = Node("BLOCK", [], t.line, t.line)
                stack[-1].children.append(pending)
            stack.append(pending)
            pending = None
        elif t.kind == "DEDENT":
            if len(stack) > 1:
                stack.pop()
        else:
            cur.append(t)
    if cur:
        stack[-1].children.append(classify_leaf(cur))
    _fix_end(root)
    return root


# --------------------------------------------------------------------------- public builders
def build_trees(source: str, spec: LanguageSpec, tokens: list[Token]) -> tuple[Node, Node]:
    """Return (ast_tree, structural_tree)."""
    if spec.key == "python":
        try:
            tree = ast.parse(source)
            struct = Node("MODULE", _py_coarse_block(tree.body), 1, source.count("\n") + 1)
            try:
                fine = _py_fine(tree)
            except RecursionError:
                fine = struct
            return fine, struct
        except (SyntaxError, ValueError, RecursionError):
            struct = parse_indent(tokens)
            return struct, struct
    struct = parse_brace(tokens)
    return struct, struct


def tree_hashes(root: Node) -> Counter[int]:
    """Multiset of subtree hashes plus adjacent-sibling windows (Deckard-style)."""
    counter: Counter[int] = Counter()

    def rec(n: Node) -> tuple[int, int]:
        hs: list[int] = []
        size = 1
        for c in n.children:
            h, s = rec(c)
            hs.append(h)
            size += s
        h = _h((n.label, tuple(hs)))
        if size >= 2:
            counter[h] += 1
        for i in range(len(hs) - 1):
            counter[_h((n.label, "sib", hs[i], hs[i + 1]))] += 1
        return h, size

    try:
        rec(root)
    except RecursionError:
        pass
    return counter


def _cf_seq(node: Node, out: list[str]) -> None:
    for c in node.children:
        if c.label in ("FUNC", "CLASS"):
            out.append(c.label)
            continue
        out.append(c.label)
        if c.children:
            out.append("(")
            _cf_seq(c, out)
            out.append(")")


def _find_funcs(node: Node, acc: list[Node]) -> None:
    for c in node.children:
        if c.label == "FUNC":
            acc.append(c)
        _find_funcs(c, acc)


def extract_functions(root: Node) -> list[FuncInfo]:
    funcs: list[FuncInfo] = []
    found: list[Node] = []
    _find_funcs(root, found)
    for f in found:
        seq: list[str] = []
        _cf_seq(f, seq)
        size = sum(1 for s in seq if s not in ("(", ")", "FUNC", "CLASS"))
        funcs.append(FuncInfo(f.name or "<anonymous>", seq, size, f.line, f.end_line))
    mod_seq: list[str] = []
    _cf_seq(root, mod_seq)
    mod_size = sum(1 for s in mod_seq if s not in ("(", ")", "FUNC", "CLASS"))
    if mod_size > 0:
        funcs.append(FuncInfo("<module>", mod_seq, mod_size, 1, root.end_line))
    return funcs


def count_labels(root: Node) -> Counter[str]:
    c: Counter[str] = Counter()

    def rec(n: Node) -> None:
        c[n.label] += 1
        for ch in n.children:
            rec(ch)

    rec(root)
    return c
