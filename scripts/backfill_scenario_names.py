#!/usr/bin/env python3
"""One-time backfill: move each ``.feature``'s description into the scenario name.

tech-04 (D1) makes the feature *description* optional and promotes the
*scenario name* to the case's primary identifier. Legacy files created
before that change carry their identity in ``description`` with an empty
``scenario.name``. This script brings them up to the new baseline in one
idempotent pass:

- For every ``.feature`` whose ``scenario.name`` is **empty** and whose
  ``description`` is **non-empty**, set ``scenario.name`` to the description
  with any newlines replaced by ``" / "`` (scenario names are single-line,
  V5). The ``description`` is left **unchanged** (it stays as an optional
  longer note).
- Files that already have a scenario name are skipped (never overwritten),
  so re-running is safe.
- Files with an empty description have nothing to move and are skipped.

Run from the repo root, offline (no server needed):

    .venv/bin/python scripts/backfill_scenario_names.py [--data-root ./project]

Re-running is safe — already-named files are skipped.

Spec: specs/tech/04-tech-testcase-detail-revamp-NEW.md (D1 / §F).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `import app` when invoked as `python scripts/backfill_scenario_names.py`
# (Python puts scripts/ on sys.path[0], not the repo root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.errors import GherkinParseError  # noqa: E402
from app.storage import Storage  # noqa: E402


def _scenario_name_from_description(description: str) -> str:
    """The move rule: collapse newlines into ``" / "`` (single-line, V5)."""
    return description.replace("\n", " / ")


def migrate(storage: Storage) -> tuple[list[str], list[str], list[str]]:
    """Backfill scenario names from descriptions across every project.

    Returns ``(migrated, skipped, errored)`` lists of data-root-relative
    ``.feature`` paths.
    """
    migrated: list[str] = []
    skipped: list[str] = []
    errored: list[str] = []
    for project in storage.list_root():
        for path in storage.iter_feature_paths(project):
            try:
                feature = storage.read_feature(path)
            except (GherkinParseError, UnicodeDecodeError):
                errored.append(path)
                continue
            # Idempotent: never overwrite an existing scenario name, and skip
            # files with nothing to move (empty description).
            if feature.scenario.name or not feature.description:
                skipped.append(path)
                continue
            feature.scenario.name = _scenario_name_from_description(
                feature.description
            )
            storage.write_feature(path, feature)
            migrated.append(path)
    return migrated, skipped, errored


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
    migrated, skipped, errored = migrate(storage)

    print(f"Backfill scenario names over {root}")
    print(f"  migrated : {len(migrated)}")
    print(f"  skipped  : {len(skipped)} (already named or empty description)")
    if errored:
        print(f"  errored  : {len(errored)} (unparseable, left untouched) {errored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
