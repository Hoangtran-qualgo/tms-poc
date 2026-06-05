# In-progress backlog

Items observed during v1 manual verification that still need work. Grouped
by MoSCoW priority. Each entry should grow a short repro and pointer to the
relevant file(s) when picked up.

Convention: all **Investigate**-phase items default to **Should have** or
**Could have**; only file an Investigate item under **Must have** when it
is explicitly designated as such.

## Must have


## Should have

- **Investigate issue: `+ New run` button not displayed in Test
  run tab.** _Filed Jun 5, 2026 during manual verification of
  the Phase-3 test-run UI._

  The `+ New run` button is reported missing from the Test run
  sidebar tab flow. Three rendering surfaces are involved and
  the report does not yet pin which one is broken:
  - `app/templates/test_run_sidebar.html` (the sidebar tab) —
    intentionally has **no** action buttons; it's a navigation
    surface only.
  - `app/templates/folder_test_run_area.html` (the
    `/ui/folder/<project>/test-run` landing reached via the
    breadcrumb's `test-run` segment) — intentionally has no
    `+ New run`; groups are auto-created by the run-create
    flow, so the landing currently lists groups without a CTA.
  - `app/templates/folder_test_run_group.html` (the
    `/ui/folder/<project>/test-run/<group>` runs list) — **is**
    the canonical home of the toolbar `+ New run` button and
    the empty-state CTA (both call `tmsCreateRun(project,
    group)` per `specs/features/10-feature-test-run-NEW.md` §
    Templates).

  Repro steps to capture when picked up:
  1. Click the Test run sidebar tab.
  2. Expand a project; click a group leaf.
  3. Note where in the main pane the user expects the button
     vs. what renders.

  Likely outcomes:
  - **(a)** User clicked a project / group row in the sidebar
    expecting it to navigate. Sidebar rows are currently
    non-navigable (see `test_run_sidebar.html`); only run
    leaves link out. If so the fix is to make group rows
    `hx-get="/ui/folder/<project>/test-run/<group>"`.
  - **(b)** User reached `folder_test_run_area.html` and
    expected `+ New run` there. If so the fix is to either
    surface a per-group `+ New run` on each row of the area
    landing or to add a `+ New group` flow (currently groups
    only materialise via `tmsCreateRun`).
  - **(c)** Genuine bug in `folder_test_run_group.html` (CSS
    clip, JS error preventing render, htmx swap targeting the
    wrong element). If so the smoke `p3_a2_group_view.py`
    (which asserts the button is in the rendered HTML) still
    passes, suggesting a client-side rendering issue rather
    than a template regression.

- **Introduce backend test harness (`pytest`).** _Filed Jun 5, 2026.
  Low priority._ The codebase currently ships zero automated
  tests via a formal harness, though the test-run feature's
  Phase-1, Phase-2, and Phase-3 deliveries produced 27 standalone
  smoke scripts under `.smoke-scratch/` (one per scenario, no
  shared setup beyond a `tempfile.TemporaryDirectory` and a
  fresh `Storage`). Once the `pytest` harness lands, re-home
  those scripts as `pytest` functions against a temp-directory
  `Storage` fixture; keep the one-file-per-scenario discipline.
  UI smoke tests stay manual — Playwright is explicitly out of
  scope per user direction.

## Could have

- **Investigate: persist expand-state for the Test run sidebar tab.**
  _Filed Jun 5, 2026 as a Phase-2 follow-up to
  `specs/features/10-feature-test-run-NEW.md`._

  The Directory-tree tab keeps expand state across SSE refreshes
  via `tmsExpandedFolders` + `tmsRestoreTreeState`. The Test-run
  tab is **stateless** in v1: every `sse:change` re-renders it
  with all groups collapsed. Investigate whether runs / groups
  grow enough per project (heuristic: >50) that this becomes
  annoying. If yes, add a sibling Set + restore helper scoped to
  `#test-run-pane`, hooked into `htmx:afterSwap`.

- **Investigate new feature: test report.**
  - Filter test cases by condition (folder / tag / tag-presence
    percentage — e.g., what % of test cases carry tag `@xxx` and
    what % do not).
  - **Rendering**: no pie chart. Render each category as a top-level
    bullet point with a count / percentage, expandable via a
    collapse/expand drop-down that reveals the matching test cases
    underneath. All groups collapsed by default.
  - Deeper reports derived from test runs — scope TBD; nail down
    during the Investigate phase.

- **Investigate new feature: folder-level test case filter.**
  - From a folder view, filter and list test cases by contain /
    not-contain rules over:
    - a specific tag.
    - a specific group of tags (all must match / none must match).
    - any tag within a specific group of tags (at least one matches).
  - Investigate the UX (chip-based filter bar vs. modal), the query
    surface (extension of `GET /api/search` vs. a new endpoint), and
    how it interacts with the existing tree / folder views.

