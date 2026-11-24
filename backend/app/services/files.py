"""Secure handling of uploaded source files.

Uploaded code is untrusted input: it is NEVER executed, imported or compiled. Files are validated,
decoded as text, normalised and stored under random names outside any web-served directory.
"""
from __future__ import annotations

import io
import posixpath
import re
import secrets
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..core.config import get_settings
from ..detection_engine.languages import EXTENSION_TO_LANGUAGE, detect_language

ALLOWED_UPLOAD_EXTENSIONS = {".py", ".java", ".c", ".cpp", ".js", ".ts", ".zip"}
_SAFE_PART = re.compile(r"[^A-Za-z0-9._\- ]")


class UploadError(ValueError):
    """Raised for any rejected upload; message is safe to show to the user."""


@dataclass
class IncomingFile:
    filename: str  # sanitised relative path
    data: bytes
    text: str
    language_key: str


def sanitize_path(name: str) -> str:
    """Return a safe relative POSIX path or raise UploadError (blocks traversal, absolute paths, drive letters)."""
    name = name.replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:", name) or "\x00" in name:
        raise UploadError(f"Unsafe file path rejected: {name[:60]!r}")
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise UploadError(f"Path traversal rejected: {name[:60]!r}")
    cleaned = [_SAFE_PART.sub("_", p)[:100] for p in parts]
    return posixpath.join(*cleaned)[:240]


def _extension(name: str) -> str:
    return posixpath.splitext(name)[1].lower()


_BINARY_MAGIC = (b"\x7fELF", b"MZ", b"%PDF", b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"PK\x03\x04", b"Rar!", b"\x1f\x8b")


def decode_source(data: bytes, filename: str) -> str:
    if data.startswith(_BINARY_MAGIC):
        raise UploadError(f"{filename}: binary file signature detected, not source code")
    if b"\x00" in data[:8192]:
        raise UploadError(f"{filename}: binary content is not allowed")
    for enc in ("utf-8-sig", "utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        raise UploadError(f"{filename}: cannot decode as text")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _make_file(name: str, data: bytes, allowed_languages: set[str] | None) -> IncomingFile:
    settings = get_settings()
    safe = sanitize_path(name)
    ext = _extension(safe)
    if ext == ".zip" or ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise UploadError(f"File type {ext or '(none)'} is not allowed: {safe}")
    if len(data) > settings.max_upload_bytes:
        raise UploadError(f"{safe} exceeds the {settings.max_upload_bytes // 1024} KB limit")
    if not data.strip():
        raise UploadError(f"{safe} is empty")
    lang = detect_language(safe)
    assert lang is not None
    if allowed_languages is not None and lang not in allowed_languages:
        raise UploadError(f"{safe}: language '{lang}' is not accepted for this assignment")
    return IncomingFile(safe, data, decode_source(data, safe), lang)


def extract_zip(data: bytes, allowed_languages: set[str] | None) -> list[IncomingFile]:
    """Safely extract source files from a ZIP held in memory (nothing is written to disk by extraction)."""
    s = get_settings()
    if len(data) > s.max_zip_bytes:
        raise UploadError("ZIP file is too large")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UploadError("Invalid ZIP archive") from exc
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > s.max_zip_files:
        raise UploadError(f"ZIP contains more than {s.max_zip_files} files")
    total = sum(i.file_size for i in infos)
    if total > s.max_zip_uncompressed_bytes:
        raise UploadError("ZIP expands to too much data (possible zip bomb)")
    out: list[IncomingFile] = []
    for info in infos:
        name = info.filename
        if name.startswith("__MACOSX/") or posixpath.basename(name).startswith("."):
            continue
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise UploadError(f"Symbolic links are not allowed in ZIP files: {name[:60]!r}")
        if info.flag_bits & 0x1:
            raise UploadError("Encrypted ZIP files are not supported")
        ext = _extension(name)
        if ext not in ALLOWED_UPLOAD_EXTENSIONS - {".zip"}:
            continue  # silently skip non-source files such as README or images
        if info.file_size > s.max_upload_bytes:
            raise UploadError(f"{name[:60]} exceeds the per-file size limit")
        if info.compress_size and info.file_size > 10_000 and info.file_size / info.compress_size > 100:
            raise UploadError("ZIP rejected: suspicious compression ratio (possible zip bomb)")
        with zf.open(info) as fh:
            payload = fh.read(s.max_upload_bytes + 1)  # bounded read regardless of declared size
        out.append(_make_file(name, payload, allowed_languages))
    if not out:
        raise UploadError("The ZIP contains no supported source files")
    return out


def collect_files(uploads: list[tuple[str, bytes]], allowed_languages: set[str] | None) -> list[IncomingFile]:
    settings = get_settings()
    result: list[IncomingFile] = []
    for name, data in uploads:
        if _extension(name) == ".zip":
            result.extend(extract_zip(data, allowed_languages))
        else:
            result.append(_make_file(name, data, allowed_languages))
    if not result:
        raise UploadError("No files uploaded")
    if len(result) > settings.max_submission_files:
        raise UploadError(f"A submission may contain at most {settings.max_submission_files} files")
    seen: set[str] = set()
    for f in result:
        if f.filename in seen:
            raise UploadError(f"Duplicate file name in submission: {f.filename}")
        seen.add(f.filename)
    return result


def store_bytes(data: bytes, subdir: str) -> str:
    """Write to <storage>/<subdir>/<random>; returns the random stored name."""
    root = get_settings().storage_dir.resolve() / subdir
    root.mkdir(parents=True, exist_ok=True)
    stored = secrets.token_hex(16)
    (root / stored).write_bytes(data)
    return stored


def resolve_stored(subdir: str, stored_name: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", stored_name):
        raise UploadError("Invalid stored name")
    root = (get_settings().storage_dir.resolve() / subdir).resolve()
    path = (root / stored_name).resolve()
    if root not in path.parents:
        raise UploadError("Invalid path")
    return path


def language_set(language_key: str) -> set[str]:
    return {language_key} if language_key in set(EXTENSION_TO_LANGUAGE.values()) else set()
