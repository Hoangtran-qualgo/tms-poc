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

from ..errors import EnumsParseError, NameConflictError, ValidationError
from ..models import ENUM_IDENTIFIER_RE, Feature
from ._core import _ENUMS_DEFAULT_BYTES, _ENUMS_FILE_NAME


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
                if not isinstance(key, str) or not ENUM_IDENTIFIER_RE.fullmatch(
                    key
                ):
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Invalid enum key {key!r} under kind "
                            f"{kind!r}; keys must match "
                            f"{ENUM_IDENTIFIER_RE.pattern}."
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
