"""File-upload security tests (no web framework needed)."""
import io
import zipfile

import pytest

from app.core.config import get_settings
from app.services.files import UploadError, collect_files, extract_zip, resolve_stored, sanitize_path, store_bytes


def make_zip(entries: dict[str, bytes | str], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


def test_valid_single_files():
    files = collect_files([("main.py", b"print('hi')\n"), ("A.java", b"class A {}\n")], None)
    assert [(f.filename, f.language_key) for f in files] == [("main.py", "python"), ("A.java", "java")]


@pytest.mark.parametrize("name", ["evil.exe", "script.sh", "noext", "image.png", "a.php"])
def test_disallowed_extensions(name):
    with pytest.raises(UploadError):
        collect_files([(name, b"x = 1")], None)


@pytest.mark.parametrize("name", ["../etc/passwd.py", "a/../../b.py", "/abs/path.py", "C:\\win\\x.py", "..\\..\\x.py"])
def test_path_traversal_rejected(name):
    with pytest.raises(UploadError):
        sanitize_path(name)


def test_sanitize_keeps_relative_subdirs_and_cleans_chars():
    assert sanitize_path("src/lib/my file$.py") == "src/lib/my file_.py"


def test_oversized_file_rejected():
    big = b"x = 1\n" * (get_settings().max_upload_bytes // 4)
    with pytest.raises(UploadError, match="limit"):
        collect_files([("big.py", big)], None)


def test_empty_and_binary_rejected():
    with pytest.raises(UploadError):
        collect_files([("e.py", b"   \n")], None)
    with pytest.raises(UploadError, match="binary"):
        collect_files([("b.py", b"abc\x00\x01def")], None)


def test_language_restriction():
    with pytest.raises(UploadError, match="not accepted"):
        collect_files([("a.js", b"let a = 1;")], {"python"})


def test_zip_extraction_ignores_non_source_and_hidden():
    z = make_zip({"proj/main.py": "x = 1\n", "proj/README.md": "hi", "proj/.hidden.py": "y", "__MACOSX/a.py": "z", "proj/img.png": b"\x89PNG"})
    files = extract_zip(z, None)
    assert [f.filename for f in files] == ["proj/main.py"]


def test_zip_path_traversal_rejected():
    with pytest.raises(UploadError):
        extract_zip(make_zip({"../../evil.py": "x = 1\n"}), None)


def test_zip_symlink_rejected():
    with pytest.raises(UploadError, match="Symbolic"):
        extract_zip(make_zip({"ok.py": "x = 1\n"}, symlink="link.py"), None)


def test_zip_bomb_rejected():
    payload = b"a = 1\n" * 300_000  # ~1.8 MB each, compresses extremely well
    z = make_zip({f"f{i}.py": payload for i in range(12)})
    assert len(z) < get_settings().max_zip_bytes
    with pytest.raises(UploadError, match="zip bomb|too much|per-file"):
        extract_zip(z, None)


def test_zip_too_many_files():
    z = make_zip({f"f{i}.py": "x = 1\n" for i in range(get_settings().max_zip_files + 1)})
    with pytest.raises(UploadError, match="more than"):
        extract_zip(z, None)


def test_invalid_zip():
    with pytest.raises(UploadError, match="Invalid ZIP"):
        collect_files([("a.zip", b"not a zip")], None)


def test_zip_without_sources():
    with pytest.raises(UploadError, match="no supported"):
        extract_zip(make_zip({"notes.txt": "hello"}), None)


def test_duplicate_names_rejected():
    with pytest.raises(UploadError, match="Duplicate"):
        collect_files([("a.py", b"x = 1"), ("a.py", b"y = 2")], None)


def test_line_endings_normalised():
    f = collect_files([("a.py", b"x = 1\r\ny = 2\r\n")], None)[0]
    assert "\r" not in f.text


def test_storage_uses_random_names_and_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_dir", tmp_path)
    name = store_bytes(b"data", "submissions")
    assert len(name) == 32 and resolve_stored("submissions", name).read_bytes() == b"data"
    with pytest.raises(UploadError):
        resolve_stored("submissions", "../../etc/passwd")


def test_binary_signature_rejected():
    with pytest.raises(UploadError, match="binary"):
        collect_files([("evil.py", b"\x7fELF\x02\x01\x01 not python")], None)


def test_high_compression_ratio_rejected():
    z = make_zip({"big.py": "0" * 900_000})
    with pytest.raises(UploadError, match="compression ratio|zip bomb"):
        extract_zip(z, None)


def test_nested_zip_not_extracted():
    inner = make_zip({"a.py": "x = 1\n"})
    z = make_zip({"inner.zip": inner, "top.py": "y = 2\n"})
    assert [f.filename for f in extract_zip(z, None)] == ["top.py"]
