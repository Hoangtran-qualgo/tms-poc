#!/usr/bin/env python3
"""One-time backfill: ensure every project has an ``enums.yaml`` (D10).

New projects already get a default ``enums.yaml`` on create (auto-init,
``Storage.create_folder``). This script brings **legacy** projects — created
before that behaviour shipped — up to the same baseline in one idempotent
pass. It is a thin wrapper over ``Storage.init_project_enums``: for every
depth-0 project folder that has no ``enums.yaml`` it writes the default seed;
projects that already have one are skipped (never overwritten).

Run from the repo root, offline (no server needed):

    .venv/bin/python scripts/backfill_enums.py [--data-root ./project]

Re-running is safe — already-initialised projects are skipped.

Spec: specs/features/13-feature-enums-crud-NEW.md (S5 / D10).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `import app` when invoked as `python scripts/backfill_enums.py`
# (Python puts scripts/ on sys.path[0], not the repo root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.errors import NameConflictError  # noqa: E402
from app.storage import Storage  # noqa: E402


def backfill(storage: Storage) -> tuple[list[str], list[str]]:
    """Initialise enums.yaml for every project missing one.

    Returns ``(created, skipped)`` lists of project names.
    """
    created: list[str] = []
    skipped: list[str] = []
    for project in storage.list_root():
        try:
            storage.init_project_enums(project)
            created.append(project)
        except NameConflictError:
            # Already has enums.yaml — leave it untouched.
            skipped.append(project)
    return created, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default="project",
        help="Path to the data root (default: ./project, matching create_app).",
    )
    args = parser.parse_args(argv)

    root = Path(args.data_root).resolve()
    if not root.is_dir():
        print(f"error: data root does not exist: {root}", file=sys.stderr)
        return 1

    storage = Storage(root)
    created, skipped = backfill(storage)

    print(f"Backfill enums over {root}")
    print(f"  created : {len(created)} {created if created else ''}".rstrip())
    print(f"  skipped : {len(skipped)} (already had enums.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
