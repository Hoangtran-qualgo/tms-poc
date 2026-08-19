"""Folder mutation mixin: create / rename / delete folders, move + duplicate files."""

from __future__ import annotations

from contextlib import ExitStack
import os
import shutil

from ..errors import NameConflictError
from ._core import (
    MAX_FOLDER_DEPTH,
    PartsLike,
    _ENUMS_DEFAULT_BYTES,
    _ENUMS_FILE_NAME,
    _REPORT_AREA,
    _RUN_EXT,
    _TEST_RUN_AREA,
    TEMP_FILE_RE,
    _normalize_filename,
)


class FoldersMixin:
    """Folder writes plus cross-folder file move / duplicate."""

    @staticmethod
    def _relocate_reference_path(value: str, old: str, new: str) -> str:
        """Replace one exact or slash-bounded data-root-relative path."""
        if value == old:
            return new
        if value.startswith(old + "/"):
            return new + value[len(old):]
        return value

    def _reference_rewrites_for_relocation(
        self,
        source,
        target,
        old_key: str,
        new_key: str,
        project: str,
    ) -> list[tuple[object, object, bytes, bytes]]:
        """Preflight changed run/report documents for one path relocation.

        All typed metadata in the affected project is parsed before the
        physical move. This deliberately blocks a rename on malformed typed
        metadata rather than risking a silent stale reference.
        """
        project_dir = self._resolve([project])
        rewrites: list[tuple[object, object, bytes, bytes]] = []

        def relocated_document_path(path):
            if path.is_relative_to(source):
                return target / path.relative_to(source)
            return path

        run_dir = project_dir / _TEST_RUN_AREA
        if run_dir.is_dir():
            for run_path in sorted(run_dir.rglob("*")):
                if (
                    not run_path.is_file()
                    or TEMP_FILE_RE.match(run_path.name)
                    or not run_path.name.lower().endswith(_RUN_EXT)
                ):
                    continue
                before = run_path.read_bytes()
                run = self._parse_run(before.decode("utf-8"))
                changed = False
                for result in run.results:
                    updated = self._relocate_reference_path(
                        result.file_path, old_key, new_key
                    )
                    if updated != result.file_path:
                        result.file_path = updated
                        changed = True
                if changed:
                    rewrites.append(
                        (
                            run_path,
                            relocated_document_path(run_path),
                            before,
                            self._serialize_run(run),
                        )
                    )

        report_dir = project_dir / _REPORT_AREA
        if report_dir.is_dir():
            for report_path in sorted(report_dir.iterdir()):
                if (
                    not report_path.is_file()
                    or TEMP_FILE_RE.match(report_path.name)
                    or not report_path.name.lower().endswith(_RUN_EXT)
                ):
                    continue
                before = report_path.read_bytes()
                report = self._parse_report(before.decode("utf-8"))
                updated_run_paths = [
                    self._relocate_reference_path(path, old_key, new_key)
                    for path in report.run_paths
                ]
                updated_case_path = self._relocate_reference_path(
                    report.case_path, old_key, new_key
                )
                updated_scope = self._relocate_reference_path(
                    report.scope, old_key, new_key
                )
                if (
                    updated_run_paths != report.run_paths
                    or updated_case_path != report.case_path
                    or updated_scope != report.scope
                ):
                    report.run_paths = updated_run_paths
                    report.case_path = updated_case_path
                    report.scope = updated_scope
                    rewrites.append(
                        (
                            report_path,
                            relocated_document_path(report_path),
                            before,
                            self._serialize_report(report),
                        )
                    )

        return rewrites

    def _relocate_with_reference_cascade(
        self,
        source,
        target,
        old_key: str,
        new_key: str,
        project: str,
    ) -> None:
        """Rename a path and rewrite its run/report references.

        The filesystem has no multi-file transaction, so a failed metadata
        write reverses the physical move and restores already-written
        documents before the original error propagates.
        """
        rewrites = self._reference_rewrites_for_relocation(
            source, target, old_key, new_key, project
        )
        lock_keys = sorted(
            {
                path.relative_to(self.root).as_posix()
                for original, rewritten, _, _ in rewrites
                for path in (original, rewritten)
                if path.relative_to(self.root).as_posix() not in {old_key, new_key}
            }
        )
        moved = False
        written: list[tuple[object, object, bytes, bytes]] = []
        with ExitStack() as stack:
            for key in lock_keys:
                stack.enter_context(self._lock_for(key))
            try:
                os.replace(source, target)
                moved = True
                for rewrite in rewrites:
                    _, rewritten, _, data = rewrite
                    self._atomic_write_bytes(rewritten, data)
                    written.append(rewrite)
            except BaseException:
                if moved:
                    try:
                        os.replace(target, source)
                    except OSError:
                        pass
                for original, _, data, _ in written:
                    try:
                        self._atomic_write_bytes(original, data)
                    except OSError:
                        pass
                raise

        self._mark_write(source)
        self._mark_write(target)
        for _, rewritten, _, _ in rewrites:
            self._mark_write(rewritten)

    # -- Folder writes ----------------------------------------------------

    def create_folder(self, parts: PartsLike) -> None:
        """Create a folder at depth 1..MAX_FOLDER_DEPTH.

        Depth 1 = project, depth 2 = module, depth 3..MAX = arbitrary
        sub-folder. Raises :class:`NameConflictError` if the folder already
        exists, and :class:`FileNotFoundError` if the immediate parent
        (depth ≥ 2) is missing. ``parents=False`` prevents typos in the
        parent chain from creating intermediate folders implicitly.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("create_folder requires a non-empty path.")
        for seg in segments:
            self._validate_segment(seg)
        if len(segments) > MAX_FOLDER_DEPTH:
            raise ValueError(
                f"create_folder only supports paths up to depth "
                f"{MAX_FOLDER_DEPTH}; got depth {len(segments)}."
            )
        self._reject_reserved_typed_area(segments)

        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A folder named {segments[-1]!r} already exists.",
                )
            if len(segments) >= 2 and not target.parent.is_dir():
                raise FileNotFoundError(
                    f"Parent folder does not exist: {'/'.join(segments[:-1])!r}"
                )
            target.mkdir(parents=False, exist_ok=False)
            self._mark_write(target)
            # Project-create auto-init: write the default `enums.yaml` next
            # to the newly-created project folder per spec 11. The two
            # writes are sequential, not atomic; a crash between them
            # leaves a legacy-shaped project (no enums file) that the user
            # reconciles via `Initialize enums file`. Same code path.
            if len(segments) == 1:
                enums_target = target / _ENUMS_FILE_NAME
                self._atomic_write_bytes(enums_target, _ENUMS_DEFAULT_BYTES)
                self._mark_write(enums_target)

    def rename_folder(self, parts: PartsLike, new_name: str) -> None:
        """Rename a folder within its existing parent. Any depth allowed.

        Same-parent only by construction (the destination shares the
        source's parent segments). Raises :class:`FileNotFoundError` for a
        missing source, :class:`NameConflictError` if the destination is
        already taken, and :class:`ValueError` if ``new_name`` is invalid.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("rename_folder requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_dir():
            raise FileNotFoundError(f"Folder not found: {source}")

        self._validate_segment(new_name)
        target_segments = [*segments[:-1], new_name]
        target = self._resolve(target_segments)

        if source == target:
            return  # no-op

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A folder named {new_name!r} already exists.",
                )
            self._relocate_with_reference_cascade(
                source, target, src_key, dst_key, segments[0]
            )

    def delete_folder(self, parts: PartsLike) -> None:
        """Recursively delete a folder. Idempotent on missing target.

        Any depth allowed. Raises :class:`ValueError` if ``parts`` is empty
        (would delete the data root) or if the resolved target is a file
        rather than a folder.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("Cannot delete the data root.")
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.exists():
                return  # idempotent per PLAN.md §6.2
            if not target.is_dir():
                raise ValueError(
                    f"Target is a file, not a folder: {target}"
                )
            shutil.rmtree(target)
            self._mark_write(target)

    # -- File move --------------------------------------------------------

    def move_file(
        self, parts: PartsLike, dest_parent: PartsLike
    ) -> None:
        """Move a ``.feature`` file to a different parent folder.

        The leaf (file name) is preserved — renaming is a separate operation
        (:meth:`rename_file`). The destination parent must be an existing
        folder at depth ``2..MAX_FOLDER_DEPTH`` (same rule that gates
        :meth:`create_file`); a move into the source's current parent is
        rejected as a no-op so the caller is forced to surface a clearer
        intent.

        Raises :class:`FileNotFoundError` if the source file or the
        destination parent folder is missing; :class:`NameConflictError`
        if a file of the same name already exists at the destination;
        :class:`ValueError` for invalid paths, depth out of range, or
        same-parent attempts.

        Locking mirrors :meth:`rename_file` / :meth:`duplicate_file`:
        acquires source + destination locks in sorted order to avoid
        deadlocks under concurrent moves.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("move_file requires a non-empty source path.")
        for seg in segments:
            self._validate_segment(seg)

        dest_parent_segments = self._split(dest_parent)
        for seg in dest_parent_segments:
            self._validate_segment(seg)
        if not (2 <= len(dest_parent_segments) <= MAX_FOLDER_DEPTH):
            raise ValueError(
                "move_file destination parent must be a module or sub-folder "
                f"(2..{MAX_FOLDER_DEPTH} segments); got "
                f"{len(dest_parent_segments)} segment(s)."
            )

        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        if dest_parent_segments == segments[:-1]:
            raise ValueError(
                "move_file destination parent is the same as the source "
                "parent; use rename_file or omit the move."
            )

        dest_parent_path = self._resolve(dest_parent_segments)
        if not dest_parent_path.is_dir():
            raise FileNotFoundError(
                f"Destination folder does not exist: "
                f"{'/'.join(dest_parent_segments)!r}"
            )

        leaf = segments[-1]
        target_segments = [*dest_parent_segments, leaf]
        target = self._resolve(target_segments)

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {leaf!r} already exists at "
                            f"{'/'.join(dest_parent_segments)!r}.",
                )
            os.replace(source, target)
            self._mark_write(source)
            self._mark_write(target)

    # -- File duplicate ---------------------------------------------------

    def duplicate_file(self, parts: PartsLike, new_name: str) -> None:
        """Copy a file to a new name within the same parent folder.

        Same-parent and same-extension rules as :meth:`rename_file`. Uses the
        atomic-write primitive so the destination appears in one step.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("duplicate_file requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        new_leaf = _normalize_filename(new_name)
        self._validate_segment(new_leaf)
        target_segments = [*segments[:-1], new_leaf]
        target = self._resolve(target_segments)

        if source == target:
            raise ValueError("Duplicate name must differ from source.")

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {new_leaf!r} already exists.",
                )
            data = source.read_bytes()
            self._atomic_write_bytes(target, data)
            self._mark_write(target)
