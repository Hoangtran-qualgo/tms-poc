"""Search mixin: substring search over ``.feature`` files + path iteration."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ..errors import GherkinParseError
from ._core import TEMP_FILE_RE, _is_feature_name


class SearchMixin:
    """Feature-content search + the public feature-path iterator."""

    def search(
        self,
        query: str,
        *,
        scope: str = "all",
        match: str = "text",
        case_sensitive: bool = False,
    ) -> list[dict[str, Any]]:
        """Substring-search ``.feature`` files for ``query``.

        Parameters
        ----------
        query:
            The search term. Empty/whitespace-only queries return ``[]``.
        scope:
            ``"all"`` (default), ``"project:<name>"``, or ``"module:<proj>/<mod>"``.
        match:
            ``"text"`` — substring-matches ``Feature.description`` OR
            ``Feature.scenario.name`` (either field; at most one hit per
            file). ``matched_field`` is reported as ``"description"`` for
            both (the badge is informational only).
            ``"tag"`` — substring-matches the union of ``Feature.tags`` and
            ``Scenario.tags`` (D10). Other fields are not searched in v1 per
            PLAN.md §13.
        case_sensitive:
            Default ``False`` (case-insensitive substring match).

        Returns a list of :class:`SearchHit`-shaped dicts (see PLAN.md §16.8).
        For ``match="tag"`` a file with multiple matching tags emits one hit
        per matching tag so the UI can display which tag matched. For
        ``match="text"`` at most one hit per file is emitted.

        ``match_value`` semantics per decision G6:

        - ``text`` mode: the caller's ``query`` string echoed back.
        - ``tag`` mode: the matched tag value (without the leading ``@``).
        """
        if not query or not query.strip():
            return []
        if match not in ("text", "tag"):
            raise ValueError(
                f"Invalid match mode: {match!r}. Must be 'text' or 'tag'."
            )

        base_segments = self._scope_to_segments(scope)
        base = self._resolve(base_segments) if base_segments else self.root
        if not base.is_dir():
            return []

        needle = query if case_sensitive else query.lower()
        hits: list[dict[str, Any]] = []

        for path in self._iter_feature_files(base):
            rel = path.relative_to(self.root).as_posix()
            try:
                feature = self.read_feature(rel)
            except (GherkinParseError, OSError, UnicodeDecodeError):
                # Unparseable files are silent — surface them via the tree /
                # module listing where the user can repair them.
                continue

            if match == "text":
                if case_sensitive:
                    desc_hay, name_hay = feature.description, feature.scenario.name
                else:
                    desc_hay = feature.description.lower()
                    name_hay = feature.scenario.name.lower()
                if needle in desc_hay or needle in name_hay:
                    hits.append(
                        {
                            "file_path": rel,
                            "description": feature.description,
                            "scenario_name": feature.scenario.name,
                            "matched_field": "description",
                            "match_value": query,
                        }
                    )
            else:  # match == "tag"
                # A case's tags are the union of feature-level and
                # scenario-level tags (D10), order-preserving + de-duped so a
                # tag carried at both levels yields a single hit.
                case_tags = dict.fromkeys(
                    [*feature.tags, *feature.scenario.tags]
                )
                for tag in case_tags:
                    tag_hay = tag if case_sensitive else tag.lower()
                    if needle in tag_hay:
                        hits.append(
                            {
                                "file_path": rel,
                                "description": feature.description,
                                "scenario_name": feature.scenario.name,
                                "matched_field": "tag",
                                "match_value": tag,
                            }
                        )

        return hits

    @staticmethod
    def _scope_to_segments(scope: str) -> list[str]:
        """Parse a scope token into a list of path segments rooted at the data root.

        Raises :class:`ValueError` on any malformed scope.
        """
        if scope in ("", "all"):
            return []
        if scope.startswith("project:"):
            name = scope[len("project:"):]
            if not name or "/" in name:
                raise ValueError(
                    f"project scope must be 'project:<name>', got {scope!r}"
                )
            return [name]
        if scope.startswith("module:"):
            parts = [p for p in scope[len("module:"):].split("/") if p]
            if len(parts) != 2:
                raise ValueError(
                    f"module scope must be 'module:<proj>/<mod>', got {scope!r}"
                )
            return parts
        raise ValueError(
            f"Invalid scope: {scope!r}. "
            "Must be 'all', 'project:<name>', or 'module:<proj>/<mod>'."
        )

    def _iter_feature_files(self, base):
        """Yield every ``.feature`` file under ``base``, excluding temp orphans."""
        for path in base.rglob("*"):
            if (
                path.is_file()
                and _is_feature_name(path.name)
                and not TEMP_FILE_RE.match(path.name)
            ):
                yield path

    def iter_feature_paths(self, scope: str) -> Iterator[str]:
        """Yield data-root-relative POSIX paths of every ``.feature`` under
        ``scope``.

        ``scope`` is a data-root-relative POSIX folder path that includes the
        project (e.g. ``"Alpha"`` for the whole project or
        ``"Alpha/Checkout"`` for a subtree). Public read-only wrapper over
        :meth:`_iter_feature_files` so callers (the quality-report aggregation
        engine) need not touch storage internals.

        Raises :class:`FileNotFoundError` if ``scope`` does not resolve to an
        existing directory, letting render-time callers surface a tolerant
        warning rather than crash.
        """
        base = self._resolve(scope)
        if not base.is_dir():
            raise FileNotFoundError(f"Scope folder not found: {scope}")
        for path in self._iter_feature_files(base):
            yield path.relative_to(self.root).as_posix()
