"""S5 smoke — scripts/backfill_enums.py is idempotent over a mixed fixture.

Asserts:
1. Over a mix of one legacy project (no enums.yaml) and one initialised
   project, backfill creates a default file ONLY for the legacy one and
   skips the initialised one (never overwrites).
2. The created file holds the default seed; the pre-existing file is
   byte-for-byte unchanged.
3. A second run is a no-op (everything skipped).
4. main() returns 0 over a real data root.
"""
import pathlib
import tempfile

from app.storage import Storage
from app.storage._core import _ENUMS_DEFAULT_BYTES
from scripts.backfill_enums import backfill, main


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    # Initialised project (auto-init) with a customised vocab to detect
    # any accidental overwrite.
    s.create_folder(["Alpha"])
    s.write_project_enums("Alpha", {"components": {"login": "Login"}})
    alpha_before = (root / "Alpha" / "enums.yaml").read_bytes()
    # Legacy project: folder only, no enums.yaml.
    (root / "Legacy").mkdir()

    created, skipped = backfill(s)
    assert set(created) == {"Legacy"}, created
    assert set(skipped) == {"Alpha"}, skipped
    print("PASS  backfill creates only the legacy project's file; skips initialised")

    assert (root / "Legacy" / "enums.yaml").read_bytes() == _ENUMS_DEFAULT_BYTES
    assert (root / "Alpha" / "enums.yaml").read_bytes() == alpha_before
    print("PASS  legacy file = default seed; initialised file untouched")

    # Idempotent: a second pass creates nothing.
    created2, skipped2 = backfill(s)
    assert created2 == [], created2
    assert set(skipped2) == {"Alpha", "Legacy"}, skipped2
    print("PASS  re-running backfill is a no-op")

# --- 4. main() over a real data root returns 0 ----------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    Storage(root)
    (root / "P").mkdir()
    rc = main(["--data-root", str(root)])
    assert rc == 0, rc
    assert (root / "P" / "enums.yaml").read_bytes() == _ENUMS_DEFAULT_BYTES
    print("PASS  main(--data-root) returns 0 and backfills the project")
