# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / VS3 -- depth-2 `enums.yaml` folder name.

Spec VS3 says `_validate_segment` / `_reject_reserved_typed_area` were
"extended to also forbid a depth-2 folder named `enums.yaml`".

DRIFT (as-shipped): there is NO explicit segment-level reservation for
`enums.yaml`. The name is guarded only *incidentally* — project
creation auto-writes `<project>/enums.yaml` as a FILE, so a subsequent
`create_folder([<project>, "enums.yaml"])` collides with the existing
file and raises `NameConflictError`. But on a legacy project whose
enums file is absent, creating a folder literally named `enums.yaml`
**succeeds** — proving the reservation lives in the auto-init file, not
in segment validation. This smoke pins the real behaviour so the drift
is caught if an explicit reservation is ever added.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.errors import NameConflictError

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])  # auto-init writes Alpha/enums.yaml (a FILE)
    assert (root / "Alpha" / "enums.yaml").is_file()

    # --- Incidental guard: the auto-init FILE occupies the name. ---
    try:
        s.create_folder(["Alpha", "enums.yaml"])
        raise AssertionError("expected a name collision with the enums.yaml file")
    except NameConflictError:
        pass

    # --- DRIFT: with the file gone, a folder named enums.yaml is allowed. ---
    (root / "Alpha" / "enums.yaml").unlink()
    s.create_folder(["Alpha", "enums.yaml"])
    assert (root / "Alpha" / "enums.yaml").is_dir(), (
        "DRIFT pinned: no explicit depth-2 reservation — a folder named "
        "enums.yaml is creatable once the auto-init file is absent. If this "
        "now raises, the spec's VS3 reservation was implemented; update "
        "this smoke + COVERAGE."
    )

print("PASS  VS3 (drift pinned): enums.yaml name is guarded only by the auto-init file, not by segment reservation")
