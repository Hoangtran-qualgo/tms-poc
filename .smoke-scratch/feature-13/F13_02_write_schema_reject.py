"""S1 smoke — write_project_enums rejects bad payloads, file unchanged.

The serialized bytes are round-tripped through _parse_project_enums before
any write, so an invalid payload must raise EnumsParseError and leave the
existing enums.yaml byte-for-byte unchanged.

Cases:
1. Bad-identifier kind name.
2. Bad-identifier key.
3. Empty label.
4. Multi-line label.
"""
import pathlib
import tempfile

from app.errors import EnumsParseError
from app.storage import Storage


def _store(td: pathlib.Path) -> Storage:
    s = Storage(td)
    s.create_folder(["P"])
    # Seed with a known-good document so we can prove it is left untouched.
    s.write_project_enums("P", {"components": {"login": "Login"}})
    return s


def _expect_reject(data: dict, hint: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        s = _store(pathlib.Path(td))
        target = pathlib.Path(td) / "P" / "enums.yaml"
        before = target.read_bytes()
        try:
            s.write_project_enums("P", data)
        except EnumsParseError:
            pass
        else:
            raise AssertionError(f"expected EnumsParseError for {hint!r}, got success")
        after = target.read_bytes()
        assert after == before, f"file changed despite reject for {hint!r}"
        # Cache must still reflect the original document.
        assert s.read_project_enums("P") == {"components": {"login": "Login"}}
        print(f"PASS  Rejected {hint}; file + cache unchanged")


_expect_reject({"bad-kind": {"login": "Login"}}, "bad-identifier kind")
_expect_reject({"components": {"bad.key": "Bad"}}, "bad-identifier key")
_expect_reject({"components": {"login": ""}}, "empty label")
_expect_reject({"components": {"login": "Line one\nLine two"}}, "multi-line label")


# Keys may contain a dash (e.g. knowledge-base); kinds stay strict.
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))
    s.write_project_enums("P", {"components": {"knowledge-base": "Knowledge base"}})
    assert s.read_project_enums("P") == {"components": {"knowledge-base": "Knowledge base"}}
    print("PASS  Accepted dashed key 'knowledge-base' (kinds remain dash-free)")
