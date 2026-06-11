"""S5 smoke — D9 regression: creating a project auto-inits enums.yaml.

Pins the already-shipped auto-init behaviour (Storage.create_folder writes a
default enums.yaml beside every new project) so future changes can't silently
regress it — the backfill script (D10) only exists for legacy projects.

Asserts:
1. create_folder at depth 1 writes the default seed (`components:\n`).
2. The file parses to {"components": {}}.
3. A nested (depth 2) folder does NOT get its own enums.yaml.
"""
import pathlib
import tempfile

from app.storage import Storage
from app.storage._core import _ENUMS_DEFAULT_BYTES


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)

    s.create_folder(["New"])
    enums_path = root / "New" / "enums.yaml"
    assert enums_path.is_file(), "new project should auto-init enums.yaml"
    assert enums_path.read_bytes() == _ENUMS_DEFAULT_BYTES
    assert s.read_project_enums("New") == {"components": {}}
    print("PASS  new project auto-inits default enums.yaml (D9)")

    # A module folder (depth 2) is not a project and gets no enums.yaml.
    s.create_folder(["New", "module"])
    assert not (root / "New" / "module" / "enums.yaml").exists()
    print("PASS  nested folders do not get their own enums.yaml")
