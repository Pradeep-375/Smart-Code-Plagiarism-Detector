"""Token normalisation: boilerplate removal, abstraction, statements, canonical forms."""
from __future__ import annotations

from .languages import LanguageSpec
from .tokenizer import STRUCT_KINDS, Token

_STMT_START_PY = frozenset({"NEWLINE", "INDENT", "DEDENT"})


def strip_boilerplate(tokens: list[Token], spec: LanguageSpec) -> list[Token]:
    """Remove imports/includes/package lines and bare docstrings.

    These are shared by almost every submission and carry no evidence of copying.
    """
    out: list[Token] = []
    n = len(tokens)
    i = 0
    key = spec.key
    while i < n:
        t = tokens[i]
        if key == "python":
            at_start = not out or out[-1].kind in _STMT_START_PY
            if at_start and t.kind == "KEYWORD" and t.text in ("import", "from"):
                while i < n and tokens[i].kind != "NEWLINE":
                    i += 1
                i += 1
                continue
            if at_start and t.kind == "STRING" and (i + 1 >= n or tokens[i + 1].kind == "NEWLINE"):
                i += 2
                continue
        else:
            at_start = not out or (out[-1].kind == "OP" and out[-1].text in (";", "{", "}"))
            if at_start and t.kind == "KEYWORD":
                if key == "java" and t.text in ("import", "package"):
                    while i < n and tokens[i].text != ";":
                        i += 1
                    i += 1
                    continue
                if key == "cpp" and t.text == "using":
                    while i < n and tokens[i].text != ";":
                        i += 1
                    i += 1
                    continue
                if (
                    key in ("javascript", "typescript")
                    and t.text == "import"
                    and not (i + 1 < n and tokens[i + 1].text == "(")
                ):
                    while i < n and tokens[i].kind != "STRING":
                        i += 1
                    i += 1
                    if i < n and tokens[i].text == ";":
                        i += 1
                    continue
        out.append(t)
        i += 1
    return out


def abstract(tok: Token) -> str:
    """Language-independent abstract symbol of a token."""
    k = tok.kind
    if k == "IDENT":
        return "ID"
    if k == "NUMBER":
        return "NUM"
    if k == "STRING":
        return "STR"
    if k == "NEWLINE":
        return "NL"
    if k == "INDENT":
        return "IND"
    if k == "DEDENT":
        return "DED"
    return tok.text


def split_statements(tokens: list[Token], spec: LanguageSpec) -> list[list[Token]]:
    """Split a token stream into statements (compound-statement headers are statements too)."""
    stmts: list[list[Token]] = []
    cur: list[Token] = []
    if spec.indent_sensitive:
        for t in tokens:
            if t.kind == "NEWLINE":
                if cur:
                    stmts.append(cur)
                cur = []
            elif t.kind in STRUCT_KINDS:
                continue
            else:
                cur.append(t)
        if cur:
            stmts.append(cur)
        return stmts

    paren = 0
    for t in tokens:
        if t.kind == "OP":
            if t.text in ("(", "["):
                paren += 1
            elif t.text in (")", "]"):
                paren = max(0, paren - 1)
            elif t.text in (";", "{", "}") and paren == 0:
                if cur:
                    stmts.append(cur)
                cur = []
                continue
        cur.append(t)
    if cur:
        stmts.append(cur)
    return stmts


_AUG = {
    "+=": "+", "-=": "-", "*=": "*", "/=": "/", "%=": "%", "//=": "//", "**=": "**",
    "&=": "&", "|=": "|", "^=": "^", "<<=": "<<", ">>=": ">>",
}
_ACCESS = (".", "->", "::")


def _pop_lhs(res: list[str]) -> list[str]:
    j = len(res)
    while True:
        if j > 0 and res[j - 1] == "]":
            depth = 0
            k = j - 1
            while k >= 0:
                if res[k] == "]":
                    depth += 1
                elif res[k] == "[":
                    depth -= 1
                    if depth == 0:
                        break
                k -= 1
            if k < 0:
                break
            j = k
        if j > 0 and res[j - 1] == "ID":
            j -= 1
            if j > 0 and res[j - 1] in _ACCESS:
                j -= 1
                continue
        break
    lhs = res[j:]
    del res[j:]
    return lhs


def canonicalize(symbols: list[str]) -> list[str]:
    """Canonical form of a statement so that equivalent spellings compare equal.

    * ``x += 1``, ``x++``, ``++x``  ->  ``x = x + 1``
    * JavaScript ``let``/``const``/``var`` -> ``VAR``
    """
    res: list[str] = []
    i = 0
    n = len(symbols)
    while i < n:
        s = symbols[i]
        if s in ("++", "--"):
            op = "+" if s == "++" else "-"
            if res and res[-1] == "ID":
                lhs = _pop_lhs(res)
                res.extend(lhs + ["="] + lhs + [op, "NUM"])
            elif i + 1 < n and symbols[i + 1] == "ID":
                res.extend(["ID", "=", "ID", op, "NUM"])
                i += 1
            else:
                res.append(s)
        elif s in _AUG:
            lhs = _pop_lhs(res)
            if lhs:
                res.extend(lhs + ["="] + lhs + [_AUG[s]])
            else:
                res.append(s)
        elif s in ("let", "const", "var"):
            res.append("VAR")
        else:
            res.append(s)
        i += 1
    return res
