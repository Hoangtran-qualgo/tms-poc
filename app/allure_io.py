"""Pure Allure-2 single-file report parser (feature-15 DO-1).

Text in / dataclasses out. No FS, no HTTP.

An Allure 2 single-file report (``index.html``) embeds every data file as
``d('<path>','<base64-of-bytes>')`` calls inside a deferred ``<script>``.
This module extracts the two keys it needs — ``data/suites.json`` (the suite
tree whose leaves are the executed tests) and ``widgets/summary.json`` (for
the report's created time) — flattens the tree's leaves into
``(scenario name, RUN_RESULTS value)`` pairs, and returns a
:class:`ParsedReport`.

Behaviour locked in ``specs/features/15-feature-import-test-run-NEW.md``:

- **Status map (IR-3):** ``passed -> PASSED``, ``failed -> FAILED``,
  ``broken -> FAILED``, ``skipped -> SKIPPED``, ``unknown -> SKIPPED``. Any
  unrecognised status string also maps to ``SKIPPED``.
- **created_at (IR-4):** ``widgets/summary.json.time.start`` (epoch-ms) ->
  UTC ISO-8601 (``timespec="seconds"``) — the same shape ``create_run``
  produces. Falls back to the earliest leaf ``time.start`` when the summary
  is absent/malformed; raises when neither is available.
- **Retries (IR-5b):** two leaves sharing a name (case-folded) are retries of
  the same test; collapse to the **final** run (latest ``time.stop``, then
  report order).

Raises :class:`ValueError` (-> HTTP 400 ``bad_request``) when the input is not
a recognisable Allure 2 single-file report or its required data is malformed.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import re

#: Allure status string -> RUN_RESULTS value (IR-3). Any status not in this
#: map (incl. ``"unknown"`` and unrecognised strings) -> ``"SKIPPED"``.
_STATUS_MAP: dict[str, str] = {
    "passed": "PASSED",
    "failed": "FAILED",
    "broken": "FAILED",
    "skipped": "SKIPPED",
    "unknown": "SKIPPED",
}

#: Matches one ``d('<path>','<b64>')`` embedded-data call. base64 never
#: contains a single quote, so the non-greedy single-quoted captures are safe.
_D_CALL_RE = re.compile(r"d\(\s*'([^']+)'\s*,\s*'([^']*)'\s*\)")

#: Matches a Scenario-Outline example suffix at the END of an Allure leaf name,
#: e.g. ``"... -- @1.2 "`` (tech-09 DO-1). ``@<table>.<row>`` are 1-based; the
#: surrounding whitespace is tolerated (the real report emits a trailing space).
_EXAMPLE_SUFFIX_RE = re.compile(r"\s+--\s+@(\d+)\.(\d+)\s*$")

_SUITES_KEY = "data/suites.json"
_SUMMARY_KEY = "widgets/summary.json"


@dataclass(frozen=True, slots=True)
class ParsedScenario:
    """One executed test from the report, mapped to TMS terms."""

    name: str
    result: str


@dataclass(frozen=True, slots=True)
class ParsedReport:
    """The subset of an Allure report needed to build a TMS test run.

    ``created_at`` is a UTC ISO-8601 string; ``scenarios`` is ordered by each
    name's first appearance in the report, with retries already collapsed.
    """

    report_name: str
    created_at: str
    scenarios: list[ParsedScenario]


def parse_allure_report(html: str) -> ParsedReport:
    """Parse an Allure 2 single-file report into a :class:`ParsedReport`.

    Raises :class:`ValueError` when ``html`` is not a recognisable Allure 2
    single-file report or its required ``data/suites.json`` cannot be decoded.
    """
    if not isinstance(html, str):
        raise ValueError("Report must be a string.")

    blobs = dict(_D_CALL_RE.findall(html))
    if not blobs:
        raise ValueError(
            "Unsupported report format: no Allure embedded-data calls found."
        )

    suites = _decode_json(blobs, _SUITES_KEY, required=True)
    leaves = _collect_leaves(suites)

    summary = _decode_json(blobs, _SUMMARY_KEY, required=False)
    created_at = _resolve_created_at(summary, leaves)
    report_name = _resolve_report_name(summary)
    scenarios = _collapse_and_map(leaves)

    return ParsedReport(
        report_name=report_name,
        created_at=created_at,
        scenarios=scenarios,
    )


def _decode_json(
    blobs: dict[str, str], key: str, *, required: bool
) -> Any | None:
    """base64-decode + JSON-parse ``blobs[key]``.

    Returns ``None`` for an absent/undecodable optional key. Raises
    :class:`ValueError` when a ``required`` key is absent or undecodable.
    """
    raw_b64 = blobs.get(key)
    if raw_b64 is None or raw_b64 == "":
        if required:
            raise ValueError(f"Unsupported report format: missing {key!r}.")
        return None
    try:
        decoded = base64.b64decode(raw_b64, validate=True)
        return json.loads(decoded.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError) as e:
        if required:
            raise ValueError(
                f"Malformed report: could not decode {key!r}: {e}"
            ) from e
        return None


def _collect_leaves(node: Any) -> list[dict[str, Any]]:
    """Walk the suite tree depth-agnostically, returning its leaf nodes.

    A leaf is any node without a ``children`` key (Allure stores tests as
    childless nodes carrying ``name`` / ``status`` / ``time``). Internal suite
    nodes (incl. the synthetic root) carry a ``children`` list.
    """
    out: list[dict[str, Any]] = []

    def walk(n: Any) -> None:
        if not isinstance(n, dict):
            return
        children = n.get("children")
        if children is None:
            name = n.get("name")
            if isinstance(name, str) and name:
                out.append(n)
            return
        if isinstance(children, list):
            for child in children:
                walk(child)

    walk(node)
    return out


def _leaf_time(leaf: dict[str, Any], key: str) -> int | float | None:
    time = leaf.get("time")
    if isinstance(time, dict):
        value = time.get(key)
        if isinstance(value, (int, float)):
            return value
    return None


def _resolve_created_at(
    summary: Any, leaves: list[dict[str, Any]]
) -> str:
    """Return the report's created time as a UTC ISO-8601 second string."""
    start_ms: int | float | None = None
    if isinstance(summary, dict):
        time = summary.get("time")
        if isinstance(time, dict) and isinstance(
            time.get("start"), (int, float)
        ):
            start_ms = time["start"]
    if start_ms is None:
        starts = [
            s for s in (_leaf_time(lf, "start") for lf in leaves) if s is not None
        ]
        if starts:
            start_ms = min(starts)
    if start_ms is None:
        raise ValueError(
            "Malformed report: no created time "
            "(summary.time.start or leaf time.start)."
        )
    return datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat(
        timespec="seconds"
    )


def _resolve_report_name(summary: Any) -> str:
    if isinstance(summary, dict):
        name = summary.get("reportName")
        if isinstance(name, str) and name.strip():
            return name
    return "Allure Report"


def _map_status(status: Any) -> str:
    if isinstance(status, str):
        return _STATUS_MAP.get(status.lower(), "SKIPPED")
    return "SKIPPED"


def _collapse_and_map(leaves: list[dict[str, Any]]) -> list[ParsedScenario]:
    """Collapse same-name retries to the final run, then map to RUN_RESULTS.

    Same-name (case-folded) leaves keep the one with the latest ``time.stop``;
    ties (and missing stops) fall back to report order. Output order follows
    each name's first appearance.
    """
    first_index: dict[str, int] = {}
    chosen: dict[str, tuple[tuple[bool, float, int], dict[str, Any]]] = {}

    for idx, leaf in enumerate(leaves):
        name = leaf["name"]
        key = name.casefold()
        first_index.setdefault(key, idx)
        stop = _leaf_time(leaf, "stop")
        sort_key = (stop is not None, float(stop) if stop is not None else 0.0, idx)
        previous = chosen.get(key)
        if previous is None or sort_key >= previous[0]:
            chosen[key] = (sort_key, leaf)

    ordered_keys = sorted(chosen, key=lambda k: first_index[k])
    return [
        ParsedScenario(
            name=chosen[k][1]["name"],
            result=_map_status(chosen[k][1].get("status")),
        )
        for k in ordered_keys
    ]


def split_example_suffix(name: str) -> tuple[str, dict[str, int] | None]:
    """Split a Scenario-Outline example suffix off an Allure leaf name (tech-09).

    Allure renders each outline example row as ``"<base> -- @<table>.<row> "``
    (note the trailing space). Returns ``(base, {"table": t, "row": r})`` with
    1-based ints when the suffix is present, else ``(name.strip(), None)``.

    Only the canonical ``-- @<digits>.<digits>`` token anchored at the end is
    treated as a suffix; names that merely contain ``--`` are returned whole.
    """
    m = _EXAMPLE_SUFFIX_RE.search(name)
    if m is None:
        return name.strip(), None
    base = name[: m.start()].strip()
    return base, {"table": int(m.group(1)), "row": int(m.group(2))}
