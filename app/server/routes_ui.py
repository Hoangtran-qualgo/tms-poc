"""UI partials (HTML rendered into the page by HTMX).

All ``@ui`` views live here. JSON / REST lives on the ``api`` blueprint
(``routes_*`` modules); the two are kept separate so the JSON API can
evolve independently of the rendered HTML.
"""

from __future__ import annotations

from flask import render_template, request

from ..errors import GherkinParseError
from ..models import RUN_RESULTS, Scenario
from ..reporting import compute_report
from ._shared import (
    ui,
    _folder_crumbs,
    _is_feature_path,
    _storage,
    maybe_shell,
    tree_ancestors,
)


def _resolve_example(
    scenario: Scenario, example: dict[str, int]
) -> tuple[list[str] | None, list[str] | None]:
    """Resolve an outline example coordinate to its live ``(header, data row)``.

    Display-only (tech-09). Returns ``(None, None)`` when the case is not a
    Scenario Outline or the 1-based ``table`` / ``row`` fall outside the live
    ``Examples`` — so a case that changed shape degrades to base-name-only
    rather than erroring (the D3 tolerant-blank rule).
    """
    table_no = example.get("table")
    row_no = example.get("row")
    if (
        scenario.kind != "outline"
        or not isinstance(table_no, int)
        or not isinstance(row_no, int)
        or table_no < 1
        or row_no < 1
    ):
        return None, None
    try:
        table = scenario.examples[table_no - 1]
        return list(table.header), list(table.rows[row_no - 1])
    except IndexError:
        return None, None


@ui.get("/tree")
def ui_tree() -> str:
    """Render the tree pane as a fresh HTML partial.

    Called by HTMX on initial page load (server-side include) and on every
    ``sse:change`` event so the tree stays in sync with disk.
    """
    return render_template("tree.html", tree=_storage().list_tree())


@ui.get("/test-run-tree")
def ui_test_run_tree() -> str:
    """Render the Test-run sidebar tab as a fresh HTML partial.

    Aggregates the ``test-run/`` subtree of every project that has one.
    Lazily fetched the first time the user clicks the Test-run tab; once
    mounted the panel listens to ``sse:change`` like the Directory tree.
    """
    return render_template(
        "test_run_sidebar.html", tree=_storage().list_test_run_tree()
    )


@ui.get("/reports-tree")
def ui_reports_tree() -> str:
    """Render the Reports sidebar tab as a fresh HTML partial.

    Aggregates the ``report/`` subtree of every project that has one.
    Lazily fetched on the user's first click on the Reports tab; once
    mounted it listens to ``sse:change`` like the other sidebar panes.
    """
    return render_template(
        "reports_sidebar.html", tree=_storage().list_report_tree()
    )


@ui.get("/enums-tree")
def ui_enums_tree() -> str:
    """Render the Enums sidebar tab as a fresh HTML partial.

    Lists every project (depth-0 folders) with a flag marking those whose
    ``enums.yaml`` is missing (legacy). Lazily fetched on the user's first
    click on the Enums tab; once mounted it listens to ``sse:change`` like
    the other sidebar panes.
    """
    s = _storage()
    projects = [
        {"name": name, "missing": not s.has_project_enums(name)}
        for name in s.list_root()
    ]
    return render_template("enums_sidebar.html", projects=projects)


@ui.get("/enums/<project>")
def ui_enums(project: str):
    """Render the per-project enums manager into the main pane.

    Legacy projects (no ``enums.yaml``) render the Initialize state; a
    malformed file propagates as 422 ``enums_parse_error``.
    """
    shell = maybe_shell("enums")  # tech-10: top-level GET -> shell
    if shell is not None:
        return shell
    s = _storage()
    try:
        vocab = s.read_project_enums(project)
    except FileNotFoundError:
        return render_template(
            "enums_manager.html", project=project, vocab=None, missing=True
        )
    return render_template(
        "enums_manager.html", project=project, vocab=vocab, missing=False
    )


@ui.get("/folder/")
@ui.get("/folder/<path:p>")
def ui_folder(p: str = ""):
    """Render the main-pane view for a folder.

    Variants per :meth:`Storage.list_folder` (see PLAN.md §9.3):

    - Empty / root path → ``folder_root.html``: project listing.
    - Depth-1 (project) → ``folder_project.html``: module table.
    - Depth-2 (module) → ``folder_module.html``: features + sub-folders.
    - Depth-3..MAX (sub-folder) → ``folder_subfolder.html``: sub-folders
      + features; the entry point for arbitrarily nested test cases.

    Beyond MAX_FOLDER_DEPTH a 400 ``bad_request`` surfaces via the
    blueprint-wide ``ValueError`` handler (raised from `list_folder`).
    """
    s = _storage()
    segments = [x for x in p.split("/") if x] if p else []

    # tech-10: a top-level (non-HX) GET returns the full shell. The active tab
    # + tree-expand depend on whether this folder is a typed area (test-run/
    # and report/ are hidden from the Directory tree, so they own their tab).
    if len(segments) >= 2 and segments[1] == "test-run":
        # 10b: expand the test-run tree to <project> (+ the group node when the
        # URL points at a specific group).
        exp = [segments[0]]
        if len(segments) >= 3:
            exp.append(f"{segments[0]}/test-run/{segments[2]}")
        shell = maybe_shell("test-run", exp)
    elif len(segments) >= 2 and segments[1] == "report":
        shell = maybe_shell("reports", [segments[0]])
    else:
        shell = maybe_shell("tree", tree_ancestors("/".join(segments)))
    if shell is not None:
        return shell

    if len(segments) == 0:
        listing = s.list_folder("")
        return render_template(
            "folder_root.html", projects=listing["projects"]
        )

    if len(segments) == 1:
        listing = s.list_folder(segments)
        return render_template(
            "folder_project.html",
            project=segments[0],
            modules=listing["modules"],
        )

    # Typed area: <project>/test-run/[<group>]. The generic list_folder
    # would reject paths through the reserved name, so we never call it
    # here. See `specs/features/10-feature-test-run-NEW.md` § "UI flows".
    if len(segments) >= 2 and segments[1] == "test-run":
        project = segments[0]
        if len(segments) == 2:
            groups = s.list_run_groups(project)
            return render_template(
                "folder_test_run_area.html",
                project=project,
                groups=groups,
            )
        if len(segments) == 3:
            group = segments[2]
            # Sort newest first (created_at DESC), tie-break by file_name
            # ASC. Two-pass stable sort: secondary key first, then primary.
            # Unparseable runs sink to the bottom (their created_at is "").
            runs = s.list_runs(project, group)
            runs.sort(key=lambda r: r["file_name"])
            runs.sort(key=lambda r: r["created_at"] or "", reverse=True)
            return render_template(
                "folder_test_run_group.html",
                project=project,
                group=group,
                runs=runs,
            )
        # Deeper paths under test-run/ are not valid; the typed area is
        # exactly two levels (group + run file). Fall through to 404 by
        # raising FileNotFoundError so the blueprint handler responds.
        raise FileNotFoundError(
            f"Folder not found: {'/'.join(segments)}"
        )

    listing = s.list_folder(segments)
    folder_path = "/".join(segments)
    if len(segments) == 2:
        return render_template(
            "folder_module.html",
            project=segments[0],
            module=segments[1],
            module_path=folder_path,
            folders=listing.get("folders", []),
            features=listing["features"],
        )

    # Depth 3..MAX — generic sub-folder view. Render a breadcrumb of
    # ancestors so the user can navigate back up at any level.
    return render_template(
        "folder_subfolder.html",
        segments=segments,
        crumbs=_folder_crumbs(segments),
        folder_path=folder_path,
        folder_name=segments[-1],
        folders=listing["folders"],
        features=listing["features"],
    )


@ui.get("/file/<path:p>")
def ui_file(p: str):
    """Render the main-pane view for a file.

    Non-``.feature`` files render :file:`unsupported.html` per PLAN.md §9.7.
    ``.feature`` files render the structured-plus-raw editor with the parsed
    :class:`~app.models.Feature` and the raw on-disk text embedded as JSON
    for the client editor controller to bootstrap from.

    If the file is present but unparseable, the parse error propagates as a
    422 envelope via the blueprint error handler — the user is expected to
    repair the file externally or via the raw tab in a sibling file.
    """
    # tech-10: top-level GET -> shell; the Directory tree expands to the file's
    # parent folder (the leaf file has no children to expand).
    shell = maybe_shell(
        "tree", tree_ancestors(p.rsplit("/", 1)[0] if "/" in p else "")
    )
    if shell is not None:
        return shell
    if not _is_feature_path(p):
        return render_template("unsupported.html", file_path=p)
    s = _storage()
    feature = s.read_feature(p)  # raises FileNotFoundError / GherkinParseError
    raw = s.read_raw(p)
    segments = p.split("/")
    file_name = segments[-1]
    # `crumbs` covers every ancestor folder of the file (project, module,
    # any sub-folders). The file editor template iterates over it to
    # render an N-segment breadcrumb, which is what enables files to live
    # at any depth from 2 (under a module) to MAX_FOLDER_DEPTH.
    crumbs = _folder_crumbs(segments[:-1] + [file_name])
    return render_template(
        "file_editor.html",
        file_path=p,
        crumbs=crumbs,
        file_name=file_name,
        feature=feature.to_dict(),
        raw=raw,
    )


@ui.get("/run/<project>/<group>/<file_name>")
def ui_run(project: str, group: str, file_name: str):
    """Render the run editor for one run YAML file.

    Phase 3.C ships a read-only render: full breadcrumb, header buttons,
    name / description / results table. The interactive controller
    (dirty tracking, Save, Reload, Add case, SSE listener) is wired in
    Phases 3.D\u20133.G; in the meantime the buttons render but do
    nothing on click.

    Raises :class:`FileNotFoundError` if the run does not exist (a
    404 envelope is produced by the blueprint handler); raises
    :class:`~app.errors.RunParseError` on malformed YAML, surfacing as
    a 422 envelope.
    """
    # tech-10: top-level GET -> shell; 10b expands the test-run tree to the run.
    shell = maybe_shell("test-run", [project, f"{project}/test-run/{group}"])
    if shell is not None:
        return shell
    s = _storage()
    run = s.read_run(project, group, file_name)
    # Tombstone-on-render (spec § "Tombstone rendering"): a row whose
    # file_path no longer resolves to a .feature on disk is flagged so
    # the template can strike it through and show the "test case was
    # removed" override. Recomputed every render; storage doesn't
    # auto-mutate runs when their underlying cases vanish.
    run_dict = run.to_dict()
    root = s.root
    for r in run_dict["results"]:
        file_path = r["file_path"]
        missing = not (root / file_path).is_file()
        r["missing"] = missing
        # tech-05: scenario name is display-only — read live from the
        # .feature (never snapshotted into the run YAML), mirroring the
        # tolerant pattern in storage.list_folder. Tombstoned / unreadable
        # cases fall back to an empty string.
        if missing:
            r["scenario_name"] = ""
            continue
        try:
            scenario = s.read_feature(file_path).scenario
        except (GherkinParseError, OSError, UnicodeDecodeError):
            r["scenario_name"] = ""
            continue
        r["scenario_name"] = scenario.name
        # tech-09: when the result pins a Scenario-Outline example row, resolve
        # its header + matched data row live for display (also never snapshotted).
        example = r.get("example")
        if example:
            header, row = _resolve_example(scenario, example)
            if header is not None:
                r["example_header"] = header
                r["example_row"] = row
    return render_template(
        "run_editor.html",
        project=project,
        group=group,
        file_name=file_name,
        run=run_dict,
        results_options=list(RUN_RESULTS),
    )


@ui.get("/report/<project>/<file_name>")
def ui_report(project: str, file_name: str):
    """Render the report detail for one report YAML file.

    The persisted :class:`~app.models.Report` is loaded then handed to
    :func:`~app.reporting.compute_report`, which reads the live runs /
    features / enums and returns the per-type view model. The template
    branches on ``view.type`` (ranking vs trend vs inventory). Results
    are never cached: every render recomputes from current disk state.

    Raises :class:`FileNotFoundError` (404) if the report is missing and
    :class:`~app.errors.ReportParseError` (422) on malformed YAML, both
    surfaced via the UI blueprint error handlers.
    """
    # tech-10: top-level GET -> shell; 10b expands the reports tree to <project>.
    shell = maybe_shell("reports", [project])
    if shell is not None:
        return shell
    s = _storage()
    report = s.read_report(project, file_name)
    view = compute_report(s, project, report)
    return render_template(
        "report_detail.html",
        project=project,
        file_name=file_name,
        view=view,
    )


@ui.get("/search")
def ui_search():
    """Render the search results main-pane partial.

    Accepts the same query params as ``/api/search`` and delegates to
    :meth:`Storage.search`. Always returns HTML; the partial is responsible
    for rendering the three UX variants documented in PLAN.md §9.6:

    - 0 hits → "No matches"
    - 1 hit  → inline ``<script>`` that auto-navigates to the file editor
    - ≥2 hits → list view grouped by project (collapsible), each row showing
      the project-relative path + first-line description + match badge
    """
    q = request.args.get("q", "").strip()
    scope = request.args.get("scope", "all")
    match = request.args.get("match", "text")
    case_sensitive = request.args.get("case", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not q:
        return render_template(
            "search_results.html", hits=[], query="", show_empty_state=True
        )
    hits = _storage().search(
        q, scope=scope, match=match, case_sensitive=case_sensitive
    )
    # Group hits by project (first path segment) for the >=2-hit list view:
    # projects sorted, hit order within a project preserved. Each hit also
    # carries a project-relative path for display; the row navigation still
    # uses the full file_path.
    by_project: dict[str, list[dict]] = {}
    for hit in hits:
        project, _, rest = hit["file_path"].partition("/")
        hit["rel_path"] = rest or hit["file_path"]
        by_project.setdefault(project, []).append(hit)
    groups = [
        {"project": project, "hits": by_project[project]}
        for project in sorted(by_project)
    ]
    return render_template(
        "search_results.html",
        hits=hits,
        groups=groups,
        query=q,
        show_empty_state=False,
    )
