"""Feature-file mixin: reads, creates, writes, deletes, renames."""

from __future__ import annotations

import os

from ..errors import NameConflictError
from ..gherkin_io import parse_feature, serialize_feature
from ..models import Feature, Scenario
from ._core import PartsLike, _normalize_filename


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

    def create_file(self, parts: PartsLike, description: str) -> None:
        """Create a new ``.feature`` file with a placeholder scenario.

        The leaf segment of ``parts`` is normalised by :func:`_normalize_filename`
        (auto-append ``.feature`` if missing; reject any other extension).
        Raises :class:`NameConflictError` if a file already exists at the
        resolved path; :class:`FileNotFoundError` if the parent folder is
        missing; :class:`~app.errors.ValidationError` if ``description`` is
        empty or otherwise invalid for write-time invariants.
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
                scenario=Scenario(kind="scenario", name=""),
            )
            # Cross-check (no-op for the default empty enums dict; kept for
            # symmetry with write_feature / write_raw so future create-time
            # enum assignment goes through the same gate).
            self._cross_check_enums(final_segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

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
