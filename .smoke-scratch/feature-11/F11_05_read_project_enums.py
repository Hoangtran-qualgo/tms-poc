"""S2.2 smoke — read_project_enums + mtime cache.

Asserts behaviour across all spec-listed branches of read_project_enums:
1. Missing file raises FileNotFoundError.
2. Default `components:\\n` bytes → {"components": {}}.
3. Empty file / comment-only → {}.
4. Well-formed YAML → ordered {kind: {key: label}}.
5. Malformed YAML → EnumsParseError with a non-zero line.
6. Non-mapping root → EnumsParseError.
7. Non-list kind value → EnumsParseError.
8. Non-dict list element → EnumsParseError.
9. Multi-key list element → EnumsParseError.
10. Bad-identifier key → EnumsParseError.
11. Multi-line label → EnumsParseError.
12. Duplicate inner key → EnumsParseError.
13. Cache returns the SAME object until mtime changes.
14. Cache re-reads after an mtime bump.
"""
import os
import pathlib
import tempfile

from app.errors import EnumsParseError
from app.storage import Storage


def _store(td: pathlib.Path, contents: bytes | None = None) -> Storage:
    s = Storage(td)
    s.create_folder(["P"])  # auto-creates P/enums.yaml with default bytes
    if contents is not None:
        (td / "P" / "enums.yaml").write_bytes(contents)
    return s


def _expect_parse_error(td, contents: bytes, hint: str):
    s = _store(td, contents)
    try:
        s.read_project_enums("P")
    except EnumsParseError as e:
        return e
    raise AssertionError(f"expected EnumsParseError for {hint!r}, got success")


# --- 1. Missing file -------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    (pathlib.Path(td) / "P").mkdir()  # project without auto-init
    try:
        s.read_project_enums("P")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing file should raise FileNotFoundError")
    print("PASS  Missing enums.yaml raises FileNotFoundError")

# --- 2. Default seed -------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))  # auto-init via create_folder
    enums = s.read_project_enums("P")
    assert enums == {"components": {}}, enums
    print("PASS  Default `components:` seed parses to {'components': {}}")

# --- 3a. Empty file --------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td), b"")
    assert s.read_project_enums("P") == {}, s.read_project_enums("P")
    print("PASS  Empty enums.yaml parses to {}")

# --- 3b. Comment-only file -------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td), b"# just a comment\n# nothing here\n")
    assert s.read_project_enums("P") == {}, s.read_project_enums("P")
    print("PASS  Comment-only enums.yaml parses to {}")

# --- 4. Well-formed multi-kind --------------------------------------------
with tempfile.TemporaryDirectory() as td:
    body = (
        b"components:\n"
        b"  - login: Login by credential\n"
        b"  - login_by_SSO: Login by SSO\n"
        b"priorities:\n"
        b"  - p0: Blocker\n"
        b"  - p1: High\n"
    )
    s = _store(pathlib.Path(td), body)
    got = s.read_project_enums("P")
    assert got == {
        "components": {
            "login": "Login by credential",
            "login_by_SSO": "Login by SSO",
        },
        "priorities": {"p0": "Blocker", "p1": "High"},
    }, got
    # Insertion order preserved
    assert list(got.keys()) == ["components", "priorities"], list(got.keys())
    assert list(got["components"].keys()) == ["login", "login_by_SSO"]
    print("PASS  Well-formed multi-kind enums.yaml parses + preserves order")

# --- 5. Malformed YAML -----------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components: [unterminated\n",
        "malformed YAML",
    )
    assert e.line >= 1, e.line
    print(f"PASS  Malformed YAML raises EnumsParseError(line={e.line})")

# --- 6. Non-mapping root ---------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(pathlib.Path(td), b"- this is a list\n", "list root")
    assert "must be a YAML mapping" in e.message, e.message
    print("PASS  Non-mapping root raises EnumsParseError")

# --- 7. Non-list kind value -----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td), b"components: {not: list}\n", "non-list value"
    )
    assert "must be a list" in e.message, e.message
    print("PASS  Non-list kind value raises EnumsParseError")

# --- 8. Non-dict list element ---------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components:\n  - just_a_string\n",
        "non-dict element",
    )
    assert "single-key mapping" in e.message, e.message
    print("PASS  Non-dict list element raises EnumsParseError")

# --- 9. Multi-key list element --------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components:\n  - {a: 1, b: 2}\n",
        "multi-key element",
    )
    assert "single-key mapping" in e.message, e.message
    print("PASS  Multi-key list element raises EnumsParseError")

# --- 10. Bad-identifier key ------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components:\n  - bad.key: Bad\n",
        "bad-identifier key",
    )
    assert "Invalid enum key" in e.message, e.message
    print("PASS  Bad-identifier key raises EnumsParseError")

# --- 11. Multi-line label --------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components:\n  - login: |\n      Line one\n      Line two\n",
        "multi-line label",
    )
    assert "single-line" in e.message, e.message
    print("PASS  Multi-line label raises EnumsParseError")

# --- 12. Duplicate inner key ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    e = _expect_parse_error(
        pathlib.Path(td),
        b"components:\n  - login: A\n  - login: B\n",
        "duplicate inner key",
    )
    assert "Duplicate enum key" in e.message, e.message
    print("PASS  Duplicate inner key raises EnumsParseError")

# --- 13 + 14. Mtime cache (hit + miss) ------------------------------------
with tempfile.TemporaryDirectory() as td:
    body = b"components:\n  - login: Login\n"
    s = _store(pathlib.Path(td), body)
    v1 = s.read_project_enums("P")
    v2 = s.read_project_enums("P")
    assert v1 is v2, "cache hit should return the SAME object"
    print("PASS  Cache returns the same parsed object on mtime hit")

    # Bump mtime by overwriting with new content + advancing mtime.
    yaml_path = pathlib.Path(td) / "P" / "enums.yaml"
    yaml_path.write_bytes(b"components:\n  - login: Renamed\n")
    new_mtime_ns = os.stat(yaml_path).st_mtime_ns + 2_000_000_000  # +2s
    os.utime(yaml_path, ns=(new_mtime_ns, new_mtime_ns))
    v3 = s.read_project_enums("P")
    assert v3 is not v1, "cache miss after mtime bump should re-read"
    assert v3 == {"components": {"login": "Renamed"}}, v3
    print("PASS  Cache invalidates and re-reads after mtime bump")
