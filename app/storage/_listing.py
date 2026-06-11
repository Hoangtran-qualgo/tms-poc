"""Listing mixin: root / tree / folder / project enumeration."""

from __future__ import annotations

from typing import Any

from ..errors import GherkinParseError
from ._core import (
    MAX_FOLDER_DEPTH,
    RESERVED_DEPTH2_NAMES,
    TEMP_FILE_RE,
    PartsLike,
    _ENUMS_FILE_NAME,
    _TEST_RUN_AREA,
    _is_feature_name,
)


class ListingMixin:
    """Read-only directory / tree enumeration (no mutations)."""

    def list_root(self) -> list[str]:
        """Return depth-0 folder names (projects), in OS listing order."""
        out: list[str] = []
        if not self.root.exists():
            return out
        for entry in self.root.iterdir():
            if entry.is_dir() and not TEMP_FILE_RE.match(entry.name):
                out.append(entry.name)
        return out

    def list_tree(self) -> dict[str, Any]:
        """Return the full recursive tree as a JSON-serialisable dict.

        Shape matches PLAN.md §16.6: a root wrapper ``{name: "", children:
        [...]}``, folder nodes carrying a ``depth`` field (root's children
        are depth 0), file nodes typed ``feature`` or ``other``. Orphan
        atomic-write temp files are filtered out at every level.
        """
        return {
            "name": "",
            "children": self._tree_children(self.root, depth=0),
        }

    def _tree_children(self, dir_path, depth: int) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        if not dir_path.exists():
            return children
        for entry in dir_path.iterdir():
            name = entry.name
            if TEMP_FILE_RE.match(name):
                continue
            # Hide the reserved typed area (test-run/) from the directory
            # tree. It lives at depth 1 (direct child of a project) and is
            # surfaced via the separate Test-run sidebar tab; see
            # `list_test_run_tree`.
            if depth == 1 and name in RESERVED_DEPTH2_NAMES:
                continue
            # Hide the project-level enums.yaml file from the directory
            # tree per spec 11. v1 has no in-app surface for editing it
            # beyond the `Initialize enums file` action; teams hand-edit
            # the file on disk.
            if depth == 1 and name == _ENUMS_FILE_NAME and entry.is_file():
                continue
            rel = entry.relative_to(self.root).as_posix()
            if entry.is_dir():
                children.append(
                    {
                        "type": "folder",
                        "name": name,
                        "depth": depth,
                        "path": rel,
                        "children": self._tree_children(entry, depth + 1),
                    }
                )
            elif entry.is_file():
                children.append(
                    {
                        "type": "feature" if _is_feature_name(name) else "other",
                        "name": name,
                        "path": rel,
                    }
                )
        return children

    def list_test_run_tree(self) -> dict[str, Any]:
        """Return the aggregated ``test-run/`` subtree of every project.

        Shape mirrors :meth:`list_tree` for template-reuse convenience but
        marks leaves with ``type: "run"`` so the Test-run sidebar template
        can render them as ``/ui/run/...`` links rather than generic files.
        Projects without a ``test-run/`` folder are omitted; the resulting
        root has no children if no project has runs yet.

        Per-node shape:

        - project: ``{type:"folder", name, depth:0, path:<project>,
          children:[<group>...]}``
        - group: ``{type:"folder", name, depth:1, path:<project>/test-run/<group>,
          children:[<run>...]}``
        - run: ``{type:"run", name:<file_name>, path:<project>/test-run/<group>/<file_name>,
          project, group, file_name}``

        Non-YAML files inside groups and any nested folders are ignored;
        the typed area's structure is fixed (see
        ``specs/features/10-feature-test-run-NEW.md``).
        """
        children: list[dict[str, Any]] = []
        if not self.root.exists():
            return {"name": "", "children": children}
        for project_entry in self.root.iterdir():
            if not project_entry.is_dir() or TEMP_FILE_RE.match(project_entry.name):
                continue
            test_run_dir = project_entry / _TEST_RUN_AREA
            if not test_run_dir.is_dir():
                continue
            project = project_entry.name
            groups: list[dict[str, Any]] = []
            for group_entry in test_run_dir.iterdir():
                if not group_entry.is_dir() or TEMP_FILE_RE.match(group_entry.name):
                    continue
                group = group_entry.name
                runs: list[dict[str, Any]] = []
                for run_entry in group_entry.iterdir():
                    name = run_entry.name
                    if TEMP_FILE_RE.match(name) or not run_entry.is_file():
                        continue
                    if not name.lower().endswith(".yaml"):
                        continue
                    runs.append(
                        {
                            "type": "run",
                            "name": name,
                            "path": f"{project}/{_TEST_RUN_AREA}/{group}/{name}",
                            "project": project,
                            "group": group,
                            "file_name": name,
                        }
                    )
                groups.append(
                    {
                        "type": "folder",
                        "name": group,
                        "depth": 1,
                        "path": f"{project}/{_TEST_RUN_AREA}/{group}",
                        "children": runs,
                    }
                )
            children.append(
                {
                    "type": "folder",
                    "name": project,
                    "depth": 0,
                    "path": project,
                    "children": groups,
                }
            )
        return {"name": "", "children": children}

    def list_projects(self) -> list[str]:
        """Return all project (depth-0) directory names, sorted.

        Backs the ``GET /api/run-groups`` endpoint's ``projects`` field
        so the "+ New run" modal's "Create new group..." sub-form can
        offer existing projects as a target. Temp-suffixed directories
        are excluded; ordering is case-insensitive ascending for stable
        UI between requests.
        """
        if not self.root.exists():
            return []
        out: list[str] = []
        for entry in self.root.iterdir():
            if not entry.is_dir() or TEMP_FILE_RE.match(entry.name):
                continue
            out.append(entry.name)
        out.sort(key=str.lower)
        return out

    def list_folder(self, parts: PartsLike) -> dict[str, Any]:
        """Return one folder's contents per PLAN.md §6.2 / §16.7.

        Variants returned by depth:

        - 0 (empty parts) → ``{kind: "root", projects: [name, ...]}``
        - 1 → ``{kind: "project", modules: [name, ...]}``
        - 2 → ``{kind: "module", folders: [name, ...], features: [...]}``
        - 3..MAX_FOLDER_DEPTH → ``{kind: "subfolder", folders: [...], features: [...]}``

        At depths 2 and beyond a folder may contain BOTH `.feature` files
        and sub-folders.

        Raises :class:`ValueError` for depth > MAX_FOLDER_DEPTH;
        :class:`FileNotFoundError` if the resolved path does not exist or
        is not a directory.

        For module / sub-folder listings, each ``.feature`` file is parsed
        best-effort to extract ``description`` and the scenario's ``tags``.
        Files that fail to parse are still listed, with empty description
        and empty tags so the user can find and repair them.
        """

        segments = self._split(parts)
        for seg in segments:
            self._validate_segment(seg)

        if len(segments) == 0:
            return {"kind": "root", "projects": self.list_root()}

        if len(segments) > MAX_FOLDER_DEPTH:
            raise ValueError(
                f"list_folder only supports paths up to depth {MAX_FOLDER_DEPTH}; "
                f"got depth {len(segments)}."
            )

        target = self._resolve(segments)
        if not target.is_dir():
            raise FileNotFoundError(f"Folder not found: {target}")

        if len(segments) == 1:
            modules: list[str] = []
            for entry in target.iterdir():
                if not entry.is_dir() or TEMP_FILE_RE.match(entry.name):
                    continue
                # Hide the reserved typed area from the project module
                # listing; runs are reached via the Test-run sidebar tab.
                if entry.name in RESERVED_DEPTH2_NAMES:
                    continue
                modules.append(entry.name)
            return {"kind": "project", "modules": modules}

        # depth >= 2 — module or sub-folder listing. Both folders and
        # features can coexist; collect each in its own list.
        folders: list[str] = []
        features: list[dict[str, Any]] = []
        for entry in target.iterdir():
            name = entry.name
            if TEMP_FILE_RE.match(name):
                continue
            if entry.is_dir():
                folders.append(name)
                continue
            if not entry.is_file():
                continue
            if not _is_feature_name(name):
                continue
            try:
                feature = self.read_feature([*segments, name])
                description = feature.description
                # A case's tags are the union of feature-level and
                # scenario-level tags (D10), order-preserving + de-duped.
                tags = list(
                    dict.fromkeys([*feature.tags, *feature.scenario.tags])
                )
            except (GherkinParseError, OSError, UnicodeDecodeError):
                description = ""
                tags = []
            features.append(
                {
                    "file_name": name,
                    "description": description,
                    "tags": tags,
                }
            )
        kind = "module" if len(segments) == 2 else "subfolder"
        return {"kind": kind, "folders": folders, "features": features}
