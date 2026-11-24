"""A small, dependency-free tokenizer shared by all supported languages.

Python sources additionally produce NEWLINE / INDENT / DEDENT tokens so that
block structure can be analysed without a full parser (and still works when the
file has syntax errors).  Token offsets refer to the newline-normalised text.
"""
from __future__ import annotations

from dataclasses import dataclass

from .languages import get_language

STRUCT_KINDS = frozenset({"NEWLINE", "INDENT", "DEDENT"})


@dataclass(slots=True)
class Token:
    kind: str  # KEYWORD IDENT NUMBER STRING OP NEWLINE INDENT DEDENT
    text: str
    line: int
    end_line: int
    start: int = 0
    end: int = 0


@dataclass
class TokenizeResult:
    tokens: list[Token]
    comments: list[str]
    total_lines: int
    preprocessor_lines: int


def normalize_newlines(source: str) -> str:
    return source.replace("\r\n", "\n").replace("\r", "\n")


def tokenize(source: str, language: str) -> TokenizeResult:
    spec = get_language(language)
    source = normalize_newlines(source)
    rx = spec.pattern()
    py = spec.indent_sensitive

    tokens: list[Token] = []
    comments: list[str] = []
    preproc = 0
    line = 1
    depth = 0
    line_start = True
    indent = 0
    stack = [0]

    for m in rx.finditer(source):
        kind = m.lastgroup
        text = m.group()
        end_line = line + text.count("\n")
        if kind == "ws":
            if py and line_start and depth == 0 and "\n" not in text:
                indent = len(text.expandtabs(4))
        elif kind == "nl":
            if py and depth == 0 and tokens and tokens[-1].kind not in STRUCT_KINDS:
                tokens.append(Token("NEWLINE", "\n", line, line, m.start(), m.end()))
            if depth == 0:
                line_start = True
                indent = 0
        elif kind in ("lcomment", "bcomment"):
            comments.append(text)
        elif kind == "preproc":
            preproc += 1
        else:
            if py and line_start and depth == 0:
                if indent > stack[-1]:
                    stack.append(indent)
                    tokens.append(Token("INDENT", "", line, line, m.start(), m.start()))
                elif indent < stack[-1]:
                    while len(stack) > 1 and indent < stack[-1]:
                        stack.pop()
                        tokens.append(Token("DEDENT", "", line, line, m.start(), m.start()))
                    if indent > stack[-1]:
                        stack.append(indent)
            line_start = False
            if kind == "ident":
                tkind = "KEYWORD" if text in spec.keywords else "IDENT"
            elif kind in ("string", "tstring", "tmpl"):
                tkind = "STRING"
            elif kind == "number":
                tkind = "NUMBER"
            else:
                tkind = "OP"
                if text in ("(", "[", "{"):
                    depth += 1
                elif text in (")", "]", "}"):
                    depth = max(0, depth - 1)
            tokens.append(Token(tkind, text, line, end_line, m.start(), m.end()))
        line = end_line

    if py:
        if tokens and tokens[-1].kind not in STRUCT_KINDS:
            tokens.append(Token("NEWLINE", "\n", line, line, len(source), len(source)))
        while len(stack) > 1:
            stack.pop()
            tokens.append(Token("DEDENT", "", line, line, len(source), len(source)))

    return TokenizeResult(tokens, comments, source.count("\n") + 1, preproc)
