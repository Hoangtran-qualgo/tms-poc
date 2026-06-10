"""Pure aggregation for the quality-report feature.

See ``specs/features/12-feature-quality-report-NEW.md``. This module has no
filesystem or HTTP access of its own: every read goes through the injected
:class:`~app.storage.Storage`. :func:`compute_report` turns a persisted
:class:`~app.models.Report` plus its *live* data sources (run files +
``.feature`` enums / tags) into a JSON-serialisable view model that the
templates branch on by ``type``.

Design invariants (spec D5–D11):

- Results recompute live; nothing here is cached on the report.
- Ranking count unit is the *distinct case* that hit the chosen status in
  at least one run (D7).
- Enums / tags are read live from the current ``.feature`` (D6).
- Missing / unparseable runs and cases never raise — they degrade into a
  ``warnings`` entry or a muted ``(removed)`` bucket (D11).
"""

from __future__ import annotations

from typing import Any, Optional

from .errors import EnumsParseError, GherkinParseError, RunParseError
from .models import Feature, Report

# Synthetic bucket values (rendered muted, pinned after the real buckets).
UNSET = "(unset)"
REMOVED = "(removed)"
UNTAGGED = "(untagged)"

# Placeholder for a case absent from a given run in a trend.
ABSENT = "—"


def compute_report(storage: Any, project: str, report: Report) -> dict[str, Any]:
    """Return the view model for ``report`` within ``project``."""
    if report.type == "enum_ranking":
        return _enum_ranking(storage, project, report)
    if report.type == "tag_ranking":
        return _tag_ranking(storage, report)
    if report.type == "case_trend":
        return _case_trend(storage, report)
    if report.type == "tag_inventory":
        return _tag_inventory(storage, report)
    raise ValueError(f"Unknown report type: {report.type!r}")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _params(report: Report) -> dict[str, str]:
    """Echo the type's config for the template header."""
    return {
        "status": report.status,
        "kind": report.kind,
        "tag": report.tag,
        "scope": report.scope,
        "case_path": report.case_path,
    }


def _envelope(
    report: Report,
    total: int,
    *,
    buckets: Optional[list[dict[str, Any]]] = None,
    trend: Optional[list[dict[str, Any]]] = None,
    warnings: Optional[list[str]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    view: dict[str, Any] = {
        "type": report.type,
        "title": report.title,
        "created_at": report.created_at,
        "total": total,
        "buckets": buckets or [],
        "trend": trend or [],
        "warnings": warnings or [],
        "params": _params(report),
    }
    if extra:
        view.update(extra)
    return view


def _split_run_path(path: str) -> Optional[tuple[str, str, str]]:
    """Split ``<project>/test-run/<group>/<file>`` into the 3 ``read_run`` args.

    Returns ``None`` for any path that does not match the typed-area shape.
    """
    parts = path.split("/")
    if len(parts) != 4 or parts[1] != "test-run":
        return None
    return parts[0], parts[2], parts[3]


def _ordered_runs(storage: Any, report: Report) -> tuple[list[tuple[str, Any]], list[str]]:
    """Read every ``run_paths`` entry, ordered by ``(created_at, path)``.

    Unresolvable / malformed / unparseable runs are skipped and recorded in
    the returned ``warnings`` list.
    """
    runs: list[tuple[str, Any]] = []
    warnings: list[str] = []
    for path in report.run_paths:
        decomposed = _split_run_path(path)
        if decomposed is None:
            warnings.append(f"Ignored malformed run path: {path}")
            continue
        proj, group, file_name = decomposed
        try:
            run = storage.read_run(proj, group, file_name)
        except (FileNotFoundError, RunParseError, ValueError, UnicodeDecodeError):
            warnings.append(f"Run not found or unreadable: {path}")
            continue
        runs.append((path, run))
    runs.sort(key=lambda pr: (pr[1].created_at, pr[0]))
    return runs, warnings


def _read_feature(
    storage: Any, cache: dict[str, Optional[Feature]], path: str
) -> Optional[Feature]:
    """Memoised ``.feature`` read. ``None`` means missing / unparseable."""
    if path in cache:
        return cache[path]
    try:
        feat: Optional[Feature] = storage.read_feature(path)
    except (FileNotFoundError, GherkinParseError, UnicodeDecodeError):
        feat = None
    cache[path] = feat
    return feat


def _case_tags(feature: Feature) -> set[str]:
    """Union of feature-level and scenario-level tags (D10)."""
    return set(feature.tags) | set(feature.scenario.tags)


def _qualifying_cases(runs: list[tuple[str, Any]], status: str) -> list[str]:
    """Distinct case ``file_path``s that recorded ``status`` in >=1 run (D7).

    First-seen order is preserved for stable downstream output.
    """
    cases: list[str] = []
    seen: set[str] = set()
    for _, run in runs:
        for r in run.results:
            if r.result == status and r.file_path not in seen:
                seen.add(r.file_path)
                cases.append(r.file_path)
    return cases


def _finalize_buckets(
    groups: dict[str, dict[str, Any]], total: int
) -> list[dict[str, Any]]:
    """Attach counts / pct and order: real buckets by count DESC then label
    ASC, with synthetic buckets pinned last in a stable order.
    """
    synthetic_order = {UNSET: 0, UNTAGGED: 1, REMOVED: 2}
    for g in groups.values():
        g["count"] = len(g["cases"])
        g["pct"] = (g["count"] / total) if total else 0.0
    real = [g for g in groups.values() if not g["synthetic"]]
    synth = [g for g in groups.values() if g["synthetic"]]
    real.sort(key=lambda g: (-g["count"], g["label"]))
    synth.sort(key=lambda g: synthetic_order.get(g["value"], 99))
    return real + synth


# ---------------------------------------------------------------------------
# Per-type aggregation
# ---------------------------------------------------------------------------


def _enum_ranking(storage: Any, project: str, report: Report) -> dict[str, Any]:
    runs, warnings = _ordered_runs(storage, report)
    cases = _qualifying_cases(runs, report.status)
    total = len(cases)

    try:
        vocab = storage.read_project_enums(project)
    except (FileNotFoundError, EnumsParseError):
        vocab = {}
        warnings.append("Project enums.yaml is missing or unreadable.")
    labels = vocab.get(report.kind, {})

    cache: dict[str, Optional[Feature]] = {}
    groups: dict[str, dict[str, Any]] = {}
    for path in cases:
        feature = _read_feature(storage, cache, path)
        if feature is None:
            value, label, synthetic = REMOVED, REMOVED, True
        else:
            key = feature.enums.get(report.kind, "")
            if not key:
                value, label, synthetic = UNSET, UNSET, True
            else:
                value, label, synthetic = key, labels.get(key, key), False
        g = groups.setdefault(
            value,
            {"value": value, "label": label, "synthetic": synthetic, "cases": []},
        )
        g["cases"].append({"file_path": path})

    buckets = _finalize_buckets(groups, total)
    return _envelope(report, total, buckets=buckets, warnings=warnings)


def _tag_ranking(storage: Any, report: Report) -> dict[str, Any]:
    runs, warnings = _ordered_runs(storage, report)
    cases = _qualifying_cases(runs, report.status)
    total = len(cases)

    cache: dict[str, Optional[Feature]] = {}
    groups: dict[str, dict[str, Any]] = {}

    def bucket(value: str, label: str, synthetic: bool, path: str) -> None:
        g = groups.setdefault(
            value,
            {"value": value, "label": label, "synthetic": synthetic, "cases": []},
        )
        g["cases"].append({"file_path": path})

    for path in cases:
        feature = _read_feature(storage, cache, path)
        if feature is None:
            bucket(REMOVED, REMOVED, True, path)
            continue
        tags = _case_tags(feature)
        if not tags:
            bucket(UNTAGGED, UNTAGGED, True, path)
            continue
        for tag in tags:
            bucket(tag, tag, False, path)

    buckets = _finalize_buckets(groups, total)
    return _envelope(report, total, buckets=buckets, warnings=warnings)


def _case_trend(storage: Any, report: Report) -> dict[str, Any]:
    runs, warnings = _ordered_runs(storage, report)
    target = report.case_path

    trend: list[dict[str, Any]] = []
    for path, run in runs:
        proj, group, file_name = _split_run_path(path)  # already validated
        result = ABSENT
        for r in run.results:
            if r.file_path == target:
                result = r.result
                break
        trend.append(
            {
                "run": file_name,
                "run_path": path,
                "created_at": run.created_at,
                "result": result,
            }
        )

    cache: dict[str, Optional[Feature]] = {}
    feature = _read_feature(storage, cache, target)
    tombstoned = feature is None
    current_enums = dict(feature.enums) if feature else {}
    current_tags = sorted(_case_tags(feature)) if feature else []

    return _envelope(
        report,
        len(trend),
        trend=trend,
        warnings=warnings,
        extra={
            "tombstoned": tombstoned,
            "current_enums": current_enums,
            "current_tags": current_tags,
        },
    )


def _tag_inventory(storage: Any, report: Report) -> dict[str, Any]:
    warnings: list[str] = []
    try:
        paths = list(storage.iter_feature_paths(report.scope))
    except (FileNotFoundError, ValueError):
        return _envelope(
            report,
            0,
            buckets=[],
            warnings=[f"Scope folder not found: {report.scope}"],
        )

    cache: dict[str, Optional[Feature]] = {}
    carrying: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for path in paths:
        feature = _read_feature(storage, cache, path)
        if feature is None:
            warnings.append(f"Unreadable feature skipped: {path}")
            continue
        if report.tag in _case_tags(feature):
            carrying.append({"file_path": path})
        else:
            missing.append({"file_path": path})

    total = len(carrying) + len(missing)
    buckets = [
        {
            "value": "carrying",
            "label": f"carrying @{report.tag}",
            "synthetic": False,
            "count": len(carrying),
            "pct": (len(carrying) / total) if total else 0.0,
            "cases": carrying,
        },
        {
            "value": "not_carrying",
            "label": "not carrying",
            "synthetic": False,
            "count": len(missing),
            "pct": (len(missing) / total) if total else 0.0,
            "cases": missing,
        },
    ]
    return _envelope(report, total, buckets=buckets, warnings=warnings)
