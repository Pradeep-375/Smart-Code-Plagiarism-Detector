"""Language specifications used by the tokenizer and the detection engine."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_PY_KW = (
    "False None True and as assert async await break class continue def del elif else except "
    "finally for from global if import in is lambda nonlocal not or pass raise return try while "
    "with yield"
).split()

_JAVA_KW = (
    "abstract assert boolean break byte case catch char class const continue default do double "
    "else enum extends final finally float for goto if implements import instanceof int interface "
    "long native new package private protected public return short static strictfp super switch "
    "synchronized this throw throws transient try void volatile while var record true false null"
).split()

_C_KW = (
    "auto break case char const continue default do double else enum extern float for goto if "
    "inline int long register restrict return short signed sizeof static struct switch typedef "
    "union unsigned void volatile while NULL"
).split()

_CPP_KW = _C_KW + (
    "class namespace template typename using new delete public private protected virtual override "
    "bool true false nullptr try catch throw this operator friend explicit constexpr noexcept "
    "static_cast dynamic_cast const_cast reinterpret_cast"
).split()

_JS_KW = (
    "break case catch class const continue debugger default delete do else export extends finally "
    "for function if import in instanceof let new return super switch this throw try typeof var "
    "void while with yield async await static true false null undefined"
).split()

_TS_KW = _JS_KW + (
    "interface enum implements namespace private protected public readonly abstract declare "
    "number string boolean any never unknown"
).split()


@dataclass(frozen=True)
class LanguageSpec:
    key: str
    display: str
    extensions: tuple[str, ...]
    keywords: frozenset[str]
    family: str                    # languages in the same family can be compared with each other
    hash_comment: bool = False     # '#' starts a comment (Python)
    block_comment: bool = True     # /* ... */ comments
    preprocessor: bool = False     # C/C++ '#include' style directives
    indent_sensitive: bool = False
    triple_quote: bool = False
    template_literal: bool = False
    string_prefix: bool = False

    def pattern(self) -> re.Pattern[str]:
        return _build_pattern(self.key)


_OPS = (
    r">>>=|\.\.\.|<<=|>>=|>>>|===|!==|\*\*=|//=|&&=|\|\|=|\?\?=|<=>|->\*|\+\+|--|->|=>|==|!=|<=|>=|"
    r"&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|::|\*\*|//|\?\?|\?\.|:=|[-+*/%=<>!&|^~?:;,.(){}\[\]@#$\\]"
)


@lru_cache(maxsize=None)
def _build_pattern(key: str) -> re.Pattern[str]:
    spec = LANGUAGES[key]
    parts: list[str] = []
    if spec.preprocessor:
        parts.append(r"(?P<preproc>^[ \t]*\#(?:[^\n\\]|\\\n|\\.)*)")
    if spec.block_comment:
        parts.append(r"(?P<bcomment>/\*.*?(?:\*/|\Z))")
    if spec.hash_comment:
        parts.append(r"(?P<lcomment>\#[^\n]*)")
    else:
        parts.append(r"(?P<lcomment>//[^\n]*)")
    prefix = r"[rRbBuUfF]{0,2}" if spec.string_prefix else ""
    if spec.triple_quote:
        parts.append(rf"(?P<tstring>{prefix}(?:'''.*?(?:'''|\Z)|\"\"\".*?(?:\"\"\"|\Z)))")
    if spec.template_literal:
        parts.append(r"(?P<tmpl>`(?:\\.|[^`\\])*`?)")
    parts.append(
        rf"(?P<string>{prefix}\"(?:\\.|[^\"\\\n])*\"?|{prefix}'(?:\\.|[^'\\\n])*'?)"
    )
    parts.append(
        r"(?P<number>(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?|"
        r"\.\d+(?:[eE][+-]?\d+)?)[uUlLfFjJ]*)"
    )
    parts.append(r"(?P<ident>[^\W\d][\w$]*|\$[\w$]*)")
    parts.append(r"(?P<nl>\n)")
    parts.append(r"(?P<ws>(?:[ \t\r\f\v]|\\\n)+)")
    parts.append(rf"(?P<op>{_OPS})")
    parts.append(r"(?P<other>.)")
    return re.compile("|".join(parts), re.S | re.M)


LANGUAGES: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        "python", "Python", (".py",), frozenset(_PY_KW), "python",
        hash_comment=True, block_comment=False, indent_sensitive=True, triple_quote=True,
        string_prefix=True,
    ),
    "java": LanguageSpec("java", "Java", (".java",), frozenset(_JAVA_KW), "java", triple_quote=True),
    "c": LanguageSpec("c", "C", (".c", ".h"), frozenset(_C_KW), "c", preprocessor=True),
    "cpp": LanguageSpec(
        "cpp", "C++", (".cpp", ".cc", ".cxx", ".hpp"), frozenset(_CPP_KW), "c", preprocessor=True
    ),
    "javascript": LanguageSpec(
        "javascript", "JavaScript", (".js", ".mjs"), frozenset(_JS_KW), "js", template_literal=True
    ),
    "typescript": LanguageSpec(
        "typescript", "TypeScript", (".ts",), frozenset(_TS_KW), "js", template_literal=True
    ),
}

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ext: spec.key for spec in LANGUAGES.values() for ext in spec.extensions
}


def get_language(name: str) -> LanguageSpec:
    try:
        return LANGUAGES[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported language: {name}") from exc


def detect_language(filename: str) -> str | None:
    dot = filename.rfind(".")
    if dot < 0:
        return None
    return EXTENSION_TO_LANGUAGE.get(filename[dot:].lower())
