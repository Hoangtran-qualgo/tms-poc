"""S1 smoke — write_project_enums round-trip identity + seed format.

Asserts:
1. read -> write_project_enums -> read is an identity on the parsed dict.
2. Kind and key insertion order is preserved on disk.
3. An empty-kind document byte-matches the default seed (`components:\n`).
4. Labels with YAML-special characters (colon, leading space, hash) round-trip.
5. write returns the freshly-parsed dict and invalidates the cache.
6. write on a legacy project (no enums.yaml) raises FileNotFoundError.
"""
import pathlib
import tempfile

from app.storage import Storage
from app.storage._core import _ENUMS_DEFAULT_BYTES


def _store(td: pathlib.Path) -> Storage:
    s = Storage(td)
    s.create_folder(["P"])  # auto-creates P/enums.yaml with the default seed
    return s


# --- 1 + 2. Round-trip identity + order preservation ----------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))
    data = {
        "components": {
            "login": "Login by credential",
            "login_by_SSO": "Login by SSO",
        },
        "priorities": {"p0": "Blocker", "p1": "High"},
    }
    returned = s.write_project_enums("P", data)
    assert returned == data, returned
    got = s.read_project_enums("P")
    assert got == data, got
    assert list(got.keys()) == ["components", "priorities"], list(got.keys())
    assert list(got["components"].keys()) == ["login", "login_by_SSO"]
    print("PASS  read -> write -> read is identity, order preserved")

# --- 3. Empty-kind document byte-matches the seed -------------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))
    s.write_project_enums("P", {"components": {}})
    raw = (pathlib.Path(td) / "P" / "enums.yaml").read_bytes()
    assert raw == _ENUMS_DEFAULT_BYTES, raw
    print("PASS  Empty `components` kind byte-matches default seed")

# --- 4. YAML-special labels round-trip ------------------------------------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))
    tricky = {
        "components": {
            "a": "Has: a colon",
            "b": " leading space",
            "c": "#hash start",
            "d": "Trailing space ",
            "e": "Plain label",
        }
    }
    s.write_project_enums("P", tricky)
    got = s.read_project_enums("P")
    assert got == tricky, got
    print("PASS  Labels with colon/space/hash round-trip exactly")

# --- 5. Cache invalidation: a second read reflects the new write ----------
with tempfile.TemporaryDirectory() as td:
    s = _store(pathlib.Path(td))
    s.write_project_enums("P", {"components": {"x": "X"}})
    v1 = s.read_project_enums("P")
    s.write_project_enums("P", {"components": {"x": "X", "y": "Y"}})
    v2 = s.read_project_enums("P")
    assert v1 == {"components": {"x": "X"}}, v1
    assert v2 == {"components": {"x": "X", "y": "Y"}}, v2
    print("PASS  write invalidates the cache; next read sees the new doc")

# --- 6. Legacy project (no enums.yaml) raises FileNotFoundError -----------
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    (pathlib.Path(td) / "Legacy").mkdir()  # project without auto-init
    try:
        s.write_project_enums("Legacy", {"components": {}})
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("write on a legacy project should raise FileNotFoundError")
    print("PASS  write on a project without enums.yaml raises FileNotFoundError")
