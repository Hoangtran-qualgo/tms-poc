"""Feature-file mixin: reads, creates, writes, deletes, renames."""

from __future__ import annotations

import os

from ..errors import ImportValidationError, NameConflictError, ValidationError
from ..gherkin_io import parse_feature, serialize_feature
from ..models import Feature, Scenario, validate_feature
from ._core import MAX_FOLDER_DEPTH, PartsLike, _normalize_filename


class FeaturesMixin:
    """``.feature`` read + mutation methods (atomic-write primitive in base)."""

    # -- Reads -----------------------------------------------------------

    def read_feature(self, parts: PartsLike) -> Feature:
        """Read and parse a ``.feature`` file.

        Raises :class:`FileNotFoundError` if the file is missing, and
        :class:`~app.errors.GherkinParseError` if the file is unparseable.
        Encoding errors (non-UTF-8) propagate as :class:`UnicodeDecodeError`.
        """
        target = self._resolve(parts)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {target}")
        text = target.read_text(encoding="utf-8")
        return parse_feature(text)

    def read_raw(self, parts: PartsLike) -> str:
        """Return the raw UTF-8 text of any file inside the data root."""
        target = self._resolve(parts)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {target}")
        return target.read_text(encoding="utf-8")

    # -- Writes / creates / mutations ------------------------------------

    def create_file(
        self, parts: PartsLike, description: str = "", *, scenario_name: str = ""
    ) -> None:
        """Create a new ``.feature`` file with a placeholder scenario.

        The leaf segment of ``parts`` is normalised by :func:`_normalize_filename`
        (auto-append ``.feature`` if missing; reject any other extension).
        ``description`` is optional (tech-04 D1) — the case identity is
        ``scenario_name``, written onto the placeholder scenario. Raises
        :class:`NameConflictError` if a file already exists at the resolved
        path; :class:`FileNotFoundError` if the parent folder is missing;
        :class:`~app.errors.ValidationError` on any other write-time invariant.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("create_file requires a non-empty path.")

        leaf = _normalize_filename(segments[-1])
        final_segments = [*segments[:-1], leaf]
        for seg in final_segments:
            self._validate_segment(seg)
        self._reject_reserved_typed_area(final_segments)

        target = self._resolve(final_segments)
        key = self._key(final_segments)
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A file named {leaf!r} already exists.",
                )
            feature = Feature(
                description=description,
                scenario=Scenario(kind="scenario", name=scenario_name),
            )
            # Cross-check (no-op for the default empty enums dict; kept for
            # symmetry with write_feature / write_raw so future create-time
            # enum assignment goes through the same gate).
            self._cross_check_enums(final_segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def create_feature_file(self, parts: PartsLike, feature: Feature) -> None:
        """Create a new ``.feature`` file from a full :class:`Feature`.

        Like :meth:`create_file` but persists an arbitrary ``feature``
        (serialised in one shot) rather than a placeholder scenario. Used by
        the import flow. Runs the same gates as :meth:`create_file`:
        leaf normalisation, per-segment validation, reserved-area rejection,
        name-conflict guard, enum cross-check, and serializer validation.

        Raises :class:`NameConflictError` if a file already exists at the
        resolved path; :class:`FileNotFoundError` if the parent folder is
        missing; :class:`~app.errors.ValidationError` on any serializer
        invariant.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("create_feature_file requires a non-empty path.")

        leaf = _normalize_filename(segments[-1])
        final_segments = [*segments[:-1], leaf]
        for seg in final_segments:
            self._validate_segment(seg)
        self._reject_reserved_typed_area(final_segments)

        target = self._resolve(final_segments)
        key = self._key(final_segments)
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A file named {leaf!r} already exists.",
                )
            self._cross_check_enums(final_segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def import_feature_cases(
        self,
        parent_parts: PartsLike,
        items: list[tuple[str, Feature]],
    ) -> list[str]:
        """Import split scenarios as new ``.feature`` files (all-or-nothing).

        ``items`` pairs a **user-supplied** ``file_name`` with the
        :class:`Feature` for one scenario (produced by
        :func:`~app.gherkin_io.split_feature_source`).

        Runs a full **pre-flight** with no writes, collecting **every**
        blocking reason (so the user fixes them in one pass) and raising
        :class:`~app.errors.ImportValidationError` if any are found:

        - each ``file_name`` normalises + passes segment validation;
        - scenario ``name`` is required (non-empty) and ``steps`` is required;
        - :func:`validate_feature` serializer invariants hold;
        - **1-level-folder-scope uniqueness** (case-insensitive): no two
          imported file names or scenario names collide with each other or
          with an existing direct child of the destination folder.

        On a clean pre-flight, writes each case via
        :meth:`create_feature_file`. If a write fails mid-batch, the
        already-written files are deleted (compensating rollback) so the
        operation is all-or-nothing. Returns the created paths on success.

        Raises :class:`FileNotFoundError` if the destination folder is
        missing, :class:`ValueError` / :class:`NameConflictError` for an
        invalid or reserved destination, and
        :class:`~app.errors.ImportValidationError` for content / conflict
        problems.
        """
        parent_segments = self._split(parent_parts)

        # --- structural destination checks (must pass to proceed) --------
        for seg in parent_segments:
            self._validate_segment(seg)
        if not (2 <= len(parent_segments) <= MAX_FOLDER_DEPTH):
            raise ValueError(
                "Import destination must be a module or sub-folder "
                f"(2..{MAX_FOLDER_DEPTH} segments); got {len(parent_segments)}."
            )
        # Reserve-area check (probe with a dummy leaf so depth-2 reservation
        # is evaluated against the destination, matching create_file).
        self._reject_reserved_typed_area([*parent_segments, "_probe.feature"])
        parent_dir = self._resolve(parent_segments)
        if not parent_dir.is_dir():
            raise FileNotFoundError(f"Folder not found: {parent_dir}")

        if not items:
            raise ImportValidationError(reasons=["No scenarios to import."])

        # --- existing direct children (file + scenario names, folders) ----
        listing = self.list_folder(parent_segments)
        existing_files = {
            f["file_name"].lower() for f in listing.get("features", [])
        }
        existing_files |= {n.lower() for n in listing.get("folders", [])}
        existing_scenarios = {
            f["scenario_name"].casefold()
            for f in listing.get("features", [])
            if f["scenario_name"]
        }

        # --- per-item collect-all validation -----------------------------
        reasons: list[str] = []
        seen_files: set[str] = set()
        seen_scenarios: set[str] = set()
        planned: list[tuple[list[str], Feature]] = []

        for idx, (raw_name, feature) in enumerate(items):
            scen_name = feature.scenario.name
            label = scen_name.strip() or f"scenario #{idx + 1}"

            leaf: str | None = None
            try:
                leaf = _normalize_filename(raw_name)
                self._validate_segment(leaf)
            except ValueError as e:
                reasons.append(f"{label}: {e}")

            if not scen_name.strip():
                reasons.append(f"scenario #{idx + 1}: scenario name is required.")
            if not feature.scenario.steps:
                reasons.append(f"{label}: scenario must have at least one step.")

            try:
                validate_feature(feature)
            except ValidationError as e:
                reasons.append(f"{label}: {e.message}")

            if leaf is not None:
                lkey = leaf.lower()
                if lkey in existing_files:
                    reasons.append(
                        f"{label}: a file named {leaf!r} already exists in "
                        f"the destination."
                    )
                elif lkey in seen_files:
                    reasons.append(
                        f"{label}: duplicate file name {leaf!r} within this "
                        f"import."
                    )
                else:
                    seen_files.add(lkey)
                planned.append(([*parent_segments, leaf], feature))

            if scen_name.strip():
                skey = scen_name.casefold()
                if skey in existing_scenarios:
                    reasons.append(
                        f"{label}: a case with scenario name "
                        f"{scen_name.strip()!r} already exists in the "
                        f"destination."
                    )
                elif skey in seen_scenarios:
                    reasons.append(
                        f"{label}: duplicate scenario name "
                        f"{scen_name.strip()!r} within this import."
                    )
                else:
                    seen_scenarios.add(skey)

        if reasons:
            raise ImportValidationError(reasons=reasons)

        # --- write phase: all-or-nothing with compensating rollback -------
        written: list[list[str]] = []
        try:
            for final_segments, feature in planned:
                self.create_feature_file(final_segments, feature)
                written.append(final_segments)
        except BaseException:
            for seg in written:
                try:
                    self.delete_file(seg)
                except Exception:
                    pass
            raise

        return [self._key(seg) for seg in written]

    def write_feature(self, parts: PartsLike, feature: Feature) -> None:
        """Serialise and atomically write an existing file's :class:`Feature`.

        Raises :class:`FileNotFoundError` if the target file does not exist
        (use :meth:`create_file` instead). The serialiser performs all
        write-time validation; raises :class:`~app.errors.ValidationError`
        on any invariant violation. Also cross-checks any non-empty
        ``feature.enums`` entries against the project's ``enums.yaml`` per
        spec 11; raises :class:`~app.errors.ValidationError` (422) on
        unknown kind / key or a missing enums.yaml.
        """
        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
            self._cross_check_enums(segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def write_raw(self, parts: PartsLike, text: str) -> None:
        """Atomically write raw text to an existing ``.feature`` file.

        Parses ``text`` first to enforce Gherkin validity (raises
        :class:`~app.errors.GherkinParseError` on bad input). Newlines are
        normalised to LF before being persisted so the file format stays
        consistent regardless of the editor's input encoding. Cross-checks
        the parsed feature's ``enums`` against the project's ``enums.yaml``
        per spec 11.
        """
        parsed = parse_feature(text)  # raises GherkinParseError on bad input
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
            self._cross_check_enums(segments[0], parsed)
            self._atomic_write_bytes(target, normalized.encode("utf-8"))
            self._mark_write(target)

    def delete_file(self, parts: PartsLike) -> None:
        """Delete a file. Idempotent: succeeds if the file was already gone."""
        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            try:
                target.unlink()
            except FileNotFoundError:
                return  # idempotent per PLAN.md §6.2
            except IsADirectoryError as e:
                raise ValueError(
                    f"Target is a directory, not a file: {target}"
                ) from e
            self._mark_write(target)

    def rename_file(self, parts: PartsLike, new_name: str) -> None:
        """Rename a file within its existing parent folder.

        ``new_name`` is normalised the same way as in :meth:`create_file`.
        Raises :class:`FileNotFoundError` if the source is missing,
        :class:`NameConflictError` if the destination name is already taken,
        and :class:`ValueError` if ``new_name`` is invalid.

        Same-parent only by construction: the destination shares the source's
        parent segments — there is no way for callers to move across folders
        via this API (per PLAN.md §6.2 / decision B2).
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("rename_file requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        new_leaf = _normalize_filename(new_name)
        self._validate_segment(new_leaf)
        target_segments = [*segments[:-1], new_leaf]
        target = self._resolve(target_segments)

        if source == target:
            return  # no-op rename

        # Acquire both locks in a stable order to avoid deadlock.
        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {new_leaf!r} already exists.",
                )
            os.replace(source, target)
            self._mark_write(source)
            self._mark_write(target)
