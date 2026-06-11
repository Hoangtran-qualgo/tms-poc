"""Project-level enums mixin (``<project>/enums.yaml``).

See specs/features/11-feature-testcase-component-NEW.md. Each project
carries one ``enums.yaml`` at its root listing the canonical
``<kind>: [- <key>: <label>]`` vocabulary used by ``Feature.enums``.
Reads are mtime-cached per project so the cross-check on every
test-case save costs one ``os.stat`` plus a dict lookup on the hot
path. Hand-edits to the file take effect on the next access.
"""

from __future__ import annotations

import yaml

from ..errors import (
    EnumInUseError,
    EnumsParseError,
    NameConflictError,
    ValidationError,
)
from ..models import ENUM_IDENTIFIER_RE, ENUM_KEY_RE, Feature
from ._core import _ENUMS_DEFAULT_BYTES, _ENUMS_FILE_NAME

#: Cap on the number of referencing case paths surfaced in usage results /
#: in-use error details (enough for a helpful message, bounded cost).
_USAGE_SAMPLE_LIMIT = 5


class EnumsMixin:
    """Read / init / parse / cross-check the project enums vocabulary."""

    def read_project_enums(self, project: str) -> dict[str, dict[str, str]]:
        """Read + parse + schema-validate ``<project>/enums.yaml``.

        Returns the outer-kind → inner ``{key: label}`` map (insertion
        order preserved). An empty file, a comment-only file, or a YAML
        document whose top-level is ``None`` normalises to ``{}``; a kind
        whose value is ``None`` or ``[]`` normalises to an empty inner map.

        Raises :class:`FileNotFoundError` if the file is missing,
        :class:`~app.errors.EnumsParseError` on malformed YAML or any
        schema violation (rules (a)–(d) in the spec).

        Cached per project keyed on ``os.stat().st_mtime_ns``; the cache
        is refreshed transparently on every mtime mismatch and on
        internal writes (``init_project_enums``).
        """
        target = self._resolve([project]) / _ENUMS_FILE_NAME
        try:
            st = target.stat()
        except FileNotFoundError:
            self._invalidate_enums_cache(project)
            raise
        mtime_ns = st.st_mtime_ns
        with self._enums_cache_lock:
            cached = self._enums_cache.get(project)
            if cached is not None and cached[0] == mtime_ns:
                return cached[1]
        try:
            raw = target.read_bytes()
        except FileNotFoundError:
            self._invalidate_enums_cache(project)
            raise
        parsed = self._parse_project_enums(raw)
        with self._enums_cache_lock:
            self._enums_cache[project] = (mtime_ns, parsed)
        return parsed

    def init_project_enums(self, project: str) -> dict[str, dict[str, str]]:
        """Write the default ``components:\\n`` file for ``project``.

        Returns the parsed enums dict (``{"components": {}}``) on success
        so the caller can update an in-memory cache without an extra
        round-trip. Raises :class:`~app.errors.NameConflictError` if the
        file already exists (no overwrite), :class:`FileNotFoundError` if
        the project folder is missing.

        Used both by the manual ``POST /api/enums/<project>`` action and
        by callers who want to reconcile a legacy project. The project-
        create auto-init in :meth:`create_folder` inlines the same bytes
        write so it can stay inside the project-folder lock region; this
        method takes its own per-path lock.
        """
        project_dir = self._resolve([project])
        if not project_dir.is_dir():
            raise FileNotFoundError(
                f"Project folder does not exist: {project!r}"
            )
        target = project_dir / _ENUMS_FILE_NAME
        key = f"{project}/{_ENUMS_FILE_NAME}"
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=(
                        f"A file named {_ENUMS_FILE_NAME!r} already "
                        f"exists under project {project!r}."
                    ),
                )
            self._atomic_write_bytes(target, _ENUMS_DEFAULT_BYTES)
            self._mark_write(target)
        self._invalidate_enums_cache(project)
        return self.read_project_enums(project)

    def write_project_enums(
        self, project: str, data: dict[str, dict[str, str]]
    ) -> dict[str, dict[str, str]]:
        """Replace ``<project>/enums.yaml`` with ``data`` (canonical YAML).

        ``data`` is the same ``{kind: {key: label}}`` shape that
        :meth:`read_project_enums` returns; kind and key insertion order is
        preserved on disk so the UI controls ordering. The serialized bytes
        are round-tripped through :meth:`_parse_project_enums` **before** any
        write, so an invalid payload (bad identifier, empty / multi-line
        label, duplicate key) raises :class:`~app.errors.EnumsParseError`
        and never touches the file.

        Manages an **existing** file: raises :class:`FileNotFoundError` if
        the project folder or its ``enums.yaml`` is missing (legacy projects
        must use the ``Initialize enums file`` action first). On success the
        cache is invalidated and the freshly-parsed dict is returned.
        """
        project_dir = self._resolve([project])
        if not project_dir.is_dir():
            raise FileNotFoundError(
                f"Project folder does not exist: {project!r}"
            )
        target = project_dir / _ENUMS_FILE_NAME
        if not target.exists():
            raise FileNotFoundError(
                f"Project {project!r} has no {_ENUMS_FILE_NAME}; run the "
                f"'Initialize enums file' action first."
            )
        for kind, entries in data.items():
            if not isinstance(entries, dict):
                raise EnumsParseError(
                    line=0,
                    column=0,
                    message=(
                        f"Value under kind {kind!r} must be a mapping of "
                        f"key -> label."
                    ),
                )
        serialized = self._serialize_project_enums(data)
        # Round-trip guard: reject a bad payload before writing anything.
        self._parse_project_enums(serialized)
        # In-use removal guard (D3): never silently orphan a referencing case.
        self._block_in_use_removals(project, data)
        key = f"{project}/{_ENUMS_FILE_NAME}"
        with self._lock_for(key):
            self._atomic_write_bytes(target, serialized)
            self._mark_write(target)
        self._invalidate_enums_cache(project)
        return self.read_project_enums(project)

    def _block_in_use_removals(
        self, project: str, data: dict[str, dict[str, str]]
    ) -> None:
        """Raise :class:`EnumInUseError` if ``data`` drops an in-use key/kind.

        Compares the current on-disk vocabulary against the incoming ``data``
        and, for every ``(kind, key)`` that would disappear (a removed key or
        a removed whole kind), checks whether any ``.feature`` still selects
        it. The first in-use removal found is reported (with a referencing
        case path) so the user knows exactly which case to clear first.
        """
        current = self.read_project_enums(project)
        for kind, entries in current.items():
            new_entries = data.get(kind) or {}
            for key in entries:
                if key in new_entries:
                    continue
                count, sample = self.count_enum_key_usage(project, kind, key)
                if count:
                    first = sample[0] if sample else "?"
                    more = f" (and {count - 1} more)" if count > 1 else ""
                    raise EnumInUseError(
                        kind=kind,
                        key=key,
                        count=count,
                        sample=sample,
                        message=(
                            f"enum {kind}: {key} is in use by test case "
                            f"{first}{more} \u2014 please clear that enum in "
                            f"the test case first."
                        ),
                    )

    def count_enum_key_usage(
        self, project: str, kind: str, key: str
    ) -> tuple[int, list[str]]:
        """Count ``.feature`` files in ``project`` whose ``enums[kind] == key``.

        Returns ``(count, sample)`` where ``sample`` holds up to
        :data:`_USAGE_SAMPLE_LIMIT` data-root-relative paths of referencing
        cases (for the in-use error message and the rename/clear preview).
        """
        count = 0
        sample: list[str] = []
        for path in self.iter_feature_paths(project):
            feature = self.read_feature(path)
            if feature.enums.get(kind) == key:
                count += 1
                if len(sample) < _USAGE_SAMPLE_LIMIT:
                    sample.append(path)
        return count, sample

    def rename_enum_key(
        self, project: str, kind: str, old_key: str, new_key: str
    ) -> int:
        """Rename ``kind.old_key`` to ``new_key``, cascading to features (D4).

        Crash-safe **alias-first** ordering under a project-scoped lock:

        1. Validate: ``new_key`` is a valid identifier; ``kind``/``old_key``
           exist; ``new_key`` is not already a key of ``kind``.
        2. **Dry-run** — parse every ``.feature`` in the project, aborting the
           whole operation (before any write) if any fails to parse, and
           collecting those that select ``old_key``.
        3. Write ``enums.yaml`` with **both** keys present (alias) so no read
           ever sees an undefined key.
        4. Rewrite each referencing feature ``old_key -> new_key``.
        5. Write ``enums.yaml`` again with ``old_key`` dropped (``new_key``
           taking its slot). Returns the number of features rewritten.

        Raises :class:`FileNotFoundError` (missing project/file),
        :class:`~app.errors.ValidationError` (unknown kind/key or invalid
        ``new_key``), :class:`~app.errors.NameConflictError` (``new_key``
        already exists), or :class:`~app.errors.GherkinParseError` (a feature
        could not be parsed during the dry-run).
        """
        with self._lock_for(project):
            vocab = self.read_project_enums(project)
            entries = vocab.get(kind)
            if entries is None or old_key not in entries:
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Unknown enum key {old_key!r} for kind {kind!r} in "
                        f"{project}/{_ENUMS_FILE_NAME}."
                    ),
                )
            if not ENUM_KEY_RE.fullmatch(new_key):
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Invalid new enum key {new_key!r}; keys must match "
                        f"{ENUM_KEY_RE.pattern}."
                    ),
                )
            if new_key == old_key:
                return 0
            if new_key in entries:
                raise NameConflictError(
                    path=f"{project}/{_ENUMS_FILE_NAME}",
                    message=(
                        f"An enum key {new_key!r} already exists under kind "
                        f"{kind!r}; cannot rename {old_key!r} onto it."
                    ),
                )

            label = entries[old_key]

            # 2. Dry-run: parse every feature, collect the referencing ones.
            affected: list[str] = []
            for path in self.iter_feature_paths(project):
                feature = self.read_feature(path)
                if feature.enums.get(kind) == old_key:
                    affected.append(path)

            # 3. Alias: add new_key alongside old_key (pure addition).
            alias = {k: dict(v) for k, v in vocab.items()}
            alias[kind][new_key] = label
            self.write_project_enums(project, alias)

            # 4. Rewrite each referencing feature old_key -> new_key.
            for path in affected:
                feature = self.read_feature(path)
                feature.enums[kind] = new_key
                self.write_feature(path, feature)

            # 5. Drop old_key, with new_key taking its slot (order preserved).
            final: dict[str, dict[str, str]] = {}
            for k, v in vocab.items():
                if k != kind:
                    final[k] = dict(v)
                    continue
                inner: dict[str, str] = {}
                for ek, el in v.items():
                    inner[new_key if ek == old_key else ek] = el
                final[k] = inner
            self.write_project_enums(project, final)

            return len(affected)

    @staticmethod
    def _serialize_project_enums(data: dict[str, dict[str, str]]) -> bytes:
        """Serialize ``{kind: {key: label}}`` to canonical ``enums.yaml`` bytes.

        Kind order = ``data`` insertion order; key order = inner-dict
        insertion order. An empty kind emits the bare ``<kind>:`` form (so a
        single empty ``components`` kind byte-matches the default seed
        ``components:\\n``). Non-empty kinds emit a 2-space-indented block
        sequence of single-key ``- <key>: <label>`` mappings, with labels
        quoted by PyYAML as needed so any single-line label round-trips.
        """
        chunks: list[str] = []
        for kind, entries in data.items():
            if not entries:
                chunks.append(f"{kind}:\n")
                continue
            seq = [{key: label} for key, label in entries.items()]
            body = yaml.safe_dump(
                seq,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
            chunks.append(f"{kind}:\n")
            for line in body.splitlines():
                chunks.append(f"  {line}\n")
        return "".join(chunks).encode("utf-8")

    def has_project_enums(self, project: str) -> bool:
        """Return whether ``<project>/enums.yaml`` exists (vs a legacy project)."""
        return (self._resolve([project]) / _ENUMS_FILE_NAME).is_file()

    def clear_project_enums(self, project: str) -> None:
        """Reset ``<project>/enums.yaml`` to the default seed (D11, block).

        "Fresh start": rewrites the file to ``_ENUMS_DEFAULT_BYTES`` (the
        same content a freshly-created project has) **without deleting it**
        (honours D8). Consistent with the D3 removal rule, this is **blocked**
        — never a silent orphan: if any ``(kind, key)`` in the current vocab
        is still referenced by a ``.feature``, raises
        :class:`~app.errors.EnumInUseError` (409) naming the in-use enum and a
        referencing case so the user clears it in the test case first.

        Raises :class:`FileNotFoundError` if the project / file is missing.
        """
        project_dir = self._resolve([project])
        if not project_dir.is_dir():
            raise FileNotFoundError(
                f"Project folder does not exist: {project!r}"
            )
        target = project_dir / _ENUMS_FILE_NAME
        if not target.exists():
            raise FileNotFoundError(
                f"Project {project!r} has no {_ENUMS_FILE_NAME}; nothing to "
                f"clear."
            )
        with self._lock_for(project):
            vocab = self.read_project_enums(project)
            for kind, entries in vocab.items():
                for key in entries:
                    count, sample = self.count_enum_key_usage(
                        project, kind, key
                    )
                    if count:
                        first = sample[0] if sample else "?"
                        more = f" (and {count - 1} more)" if count > 1 else ""
                        raise EnumInUseError(
                            kind=kind,
                            key=key,
                            count=count,
                            sample=sample,
                            message=(
                                f"Cannot clear: enum {kind}: {key} is in use "
                                f"by test case {first}{more} \u2014 please "
                                f"clear that enum in the test case first."
                            ),
                        )
            self._atomic_write_bytes(target, _ENUMS_DEFAULT_BYTES)
            self._mark_write(target)
        self._invalidate_enums_cache(project)

    def _invalidate_enums_cache(self, project: str) -> None:
        with self._enums_cache_lock:
            self._enums_cache.pop(project, None)

    @staticmethod
    def _parse_project_enums(raw: bytes) -> dict[str, dict[str, str]]:
        """Parse + schema-validate the bytes of ``<project>/enums.yaml``.

        Wraps :class:`yaml.YAMLError` into :class:`EnumsParseError` with a
        location when PyYAML reports one; enforces:

        (a) every inner list element is a single-key mapping;
        (b) every key matches :data:`ENUM_IDENTIFIER_RE`;
        (c) every label is a non-empty string with no embedded newline;
        (d) keys are unique within a kind.
        """
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None) or getattr(
                e, "context_mark", None
            )
            line = (mark.line + 1) if mark is not None else 0
            column = (mark.column + 1) if mark is not None else 0
            message = getattr(e, "problem", None) or str(e)
            raise EnumsParseError(
                line=line, column=column, message=message
            ) from e

        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise EnumsParseError(
                line=0,
                column=0,
                message=(
                    f"enums.yaml root must be a YAML mapping; "
                    f"got {type(payload).__name__}."
                ),
            )

        out: dict[str, dict[str, str]] = {}
        for kind, value in payload.items():
            if not isinstance(kind, str) or not ENUM_IDENTIFIER_RE.fullmatch(
                kind
            ):
                raise EnumsParseError(
                    line=0,
                    column=0,
                    message=(
                        f"Invalid enum kind name {kind!r}; kinds must "
                        f"match {ENUM_IDENTIFIER_RE.pattern}."
                    ),
                )
            if value is None:
                out[kind] = {}
                continue
            if not isinstance(value, list):
                raise EnumsParseError(
                    line=0,
                    column=0,
                    message=(
                        f"Value under kind {kind!r} must be a list of "
                        f"single-key mappings (- <key>: <label>); got "
                        f"{type(value).__name__}."
                    ),
                )
            inner: dict[str, str] = {}
            for i, item in enumerate(value):
                if not isinstance(item, dict) or len(item) != 1:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Element {i} under kind {kind!r} must be a "
                            f"single-key mapping (- <key>: <label>)."
                        ),
                    )
                ((key, label),) = item.items()
                if not isinstance(key, str) or not ENUM_KEY_RE.fullmatch(
                    key
                ):
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Invalid enum key {key!r} under kind "
                            f"{kind!r}; keys must match "
                            f"{ENUM_KEY_RE.pattern}."
                        ),
                    )
                if key in inner:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Duplicate enum key {key!r} under kind "
                            f"{kind!r}."
                        ),
                    )
                if not isinstance(label, str):
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be a string; got "
                            f"{type(label).__name__}."
                        ),
                    )
                if not label:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be non-empty."
                        ),
                    )
                if "\n" in label:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be single-line."
                        ),
                    )
                inner[key] = label
            out[kind] = inner
        return out

    def _cross_check_enums(self, project: str, feature: Feature) -> None:
        """Reject saves whose enums don't resolve in ``<project>/enums.yaml``.

        Skips entirely when ``feature.enums`` has no non-empty entries
        (storage never forces a value to be set; *unset* is always
        legal). Missing-file rule: when there ARE non-empty entries but
        the YAML is absent, every entry is treated as orphan and the
        save is rejected with a hint pointing at the `Initialize enums
        file` action. ``EnumsParseError`` from a malformed YAML
        propagates to the API layer as a 422 envelope.
        """
        nonempty = {k: v for k, v in feature.enums.items() if v}
        if not nonempty:
            return
        try:
            vocab = self.read_project_enums(project)
        except FileNotFoundError:
            raise ValidationError(
                field="enums",
                message=(
                    f"Cannot save enum values: project {project!r} has no "
                    f"{_ENUMS_FILE_NAME}. Run the 'Initialize enums file' "
                    f"action to create one before assigning enum values."
                ),
            )
        for kind, key in nonempty.items():
            kind_entries = vocab.get(kind)
            if kind_entries is None:
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Unknown enum kind {kind!r}; not defined in "
                        f"{project}/{_ENUMS_FILE_NAME}."
                    ),
                )
            if key not in kind_entries:
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Unknown enum key {key!r} for kind {kind!r}; "
                        f"not defined in {project}/{_ENUMS_FILE_NAME}."
                    ),
                )
