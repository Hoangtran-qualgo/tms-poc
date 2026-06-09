# feature-06 · Tree pane — coverage matrix

Step 1 audit of the smoke tests against
`specs/features/06-feature-tree-pane-NEW.md`.

## Method

- Spec source: `specs/features/06-feature-tree-pane-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Spec sub-headings under `## Public surface` (Template,
  Route, Wiring, Client state) and under `## Invariants &
  rules` (test-run hidden, Server-side initial render,
  SSE-driven refresh, Manual refresh button, Click
  navigation, Expanded-state preservation) are treated as
  **sections** for the one-smoke-per-section rule
  (Decision A). Per the Step-1 sign-off rule "split tests
  into smaller parts if the content and scope are long
  (normally more than 90 LOC)", the test-run-hidden
  section is **split into four sub-files**
  (`F06_05a` … `F06_05d`) because each of HD1/HD2/HD3 has
  its own setup + assertion shape and the four pre-existing
  `p2_*` smokes that primary-frame these rules are being
  moved into `feature-06/` per Step 2 (Q3 sign-off).
- `Status` values: `covered`, `partial` (incidental coverage
  inside a primary-other-feature smoke), `missing`, `n/a`
  (rule is documentation-only / not testable).
- `Smoke file` column carries the final target file for
  every row. Feature-06 totals **14 files**: eleven
  one-per-section files plus three extra HD-split files
  (`F06_05a` … `F06_05d`).
- **Primary-frame distinction.** Feature-06 is the tree
  partial + its HTMX wiring + the client-state JS for
  expand/collapse. The "test-run hidden" rule (HD1–HD3)
  is primary-framed by feature-06 per spec section
  *Invariants & rules → test-run/ is hidden from the
  directory tree*; the existing `p2_s1` / `p2_s2` / `p2_s5`
  / `p2_2b` smokes whose primary frame is this rule are
  being moved into `feature-06/` during Step 2. Watcher
  publish behaviour stays primary-framed in feature-03;
  sidebar shell stays primary-framed in feature-10; folder
  views' HTML stays primary-framed in feature-07.
- **Testable-shape decisions** (locked Step-1 sign-off):
  - **Q1 — Hybrid JS approach** for CS2 / CS3 / EP1 /
    EP2 / EP3 / AC3: static inspection of `app/static/app.js`
    function bodies + render-and-grep for `htmx:afterSwap`
    wiring + `re.findall` DOM-parse of `/ui/tree` HTML
    for tree shape.
  - **Q2 — End-to-end claim** for AC2: the smoke
    actually subscribes to the bus, fires an external
    FS burst, asserts one `"change"` per subscriber
    after `DEBOUNCE_SECONDS * 0.9`, AND independently
    issues `GET /ui/tree` (the HTMX-would-do GET) to
    confirm the swap target reflects the new FS state.
  - **Q3 — Restructure approach**: move the four
    primary-framed `p2_*` smokes into `feature-06/`
    during Step 2; apply this principle to subsequent
    features' audits as well.
  - **Q4 — partial count**: 7 (WR3, HD1, HD2, HD3,
    SF1, SF3, AC2). After Step 2 moves, HD1/HD2/HD3
    flip from `partial` to `covered` because their
    primary-framed smokes now live in `feature-06/`.
    Final pre-Step-4 status: covered=3, partial=4,
    missing=24.

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| TM1 | `app/templates/tree.html` defines a `render_children(children)` macro that emits one `<li>` per child of any depth. | Public surface → Template | `F06_01_template.py` | covered |
| TM2 | Folder rows render a caret `<button>` AND a name `<span>` as **separate** elements (so the caret can toggle without navigating). | Public surface → Template | `F06_01_template.py` | covered |
| TM3 | `.feature` file rows emit `<div class="tree-file">` with `hx-get` to `/ui/file/<path>`. | Public surface → Template | `F06_01_template.py` | covered |
| TM4 | Non-`.feature` file rows emit `<div class="tree-other">` with the same `/ui/file/<path>` `hx-get` (the route maps them to `unsupported.html`). | Public surface → Template | `F06_01_template.py` | covered |
| RT1 | `GET /ui/tree` renders `tree.html` with `tree = storage.list_tree()`; used by both the manual refresh button and the SSE auto-refresh. | Public surface → Route | `F06_02_route.py` | covered |
| WR1 | `app/templates/base.html`'s `<body>` carries `hx-ext="sse" sse-connect="/api/events"` — page-wide SSE subscription. | Public surface → Wiring | `F06_03_wiring.py` | covered |
| WR2 | `<aside id="tree-pane">` declares `hx-get="/ui/tree" hx-trigger="sse:change" hx-swap="innerHTML"` — partial swapped wholesale on every bus message. | Public surface → Wiring | `F06_03_wiring.py` | covered |
| WR3 | `#tree-pane` is one of two sibling panels inside `#sidebar-panels`; the sibling `#test-run-pane` is hidden by default and lazy-mounted on its first tab activation. | Public surface → Wiring | `F06_03_wiring.py` (tree-pane frame) + `feature-10/F10_81_test_run_lazy_mount.py` + `feature-10/F10_79_sidebar_shell_renders.py` (sidebar-shell primary frame in feature-10) | covered |
| CS1 | `app/static/app.js` defines `const tmsExpandedFolders = new Set()` at module scope; the Set survives tree re-renders. | Public surface → Client state | `F06_04_client_state.py` | covered |
| CS2 | `toggleTreeFolder(rowEl)` toggles the `.tree-children` sibling's `hidden` class and updates `tmsExpandedFolders` (add on expand, delete on collapse); invoked by the caret button's inline `onclick`. | Public surface → Client state | `F06_04_client_state.py` (Hybrid: static body + render-and-grep onclick) | covered |
| CS3 | `tmsRestoreTreeState()` walks `#tree-pane .tree-folder[data-path]` rows and re-expands any path present in `tmsExpandedFolders`; the function is hooked into `htmx:afterSwap` for `#tree-pane`. | Public surface → Client state | `F06_04_client_state.py` (Hybrid: static body + htmx:afterSwap wiring + DOM-parse data-path) | covered |
| HD1 | `Storage.list_tree()` filters any child literally named `"test-run"` of a **depth-1 (project)** folder. (Tree-pane-frame assertion: the `/ui/tree` HTML must not carry a `data-path="<project>/test-run"` row.) | Invariants → test-run hidden | `F06_05a_list_tree_filter.py` (moved from `p2_s1`, storage half) + `F06_05b_tree_html_filter.py` (moved from `p2_2b`, HTML half) | covered |
| HD2 | Depths other than 2 are untouched — a folder named `test-run` at depth 3 (e.g. `WebStore/Checkout/test-run/`) IS still listed in `Storage.list_tree()` and the `/ui/tree` HTML. | Invariants → test-run hidden | `F06_05d_depth3_allowed.py` (moved from `p2_s5`, storage + HTML halves after Step-3 refine) | covered |
| HD3 | `Storage.list_folder(parts)` filters `"test-run"` out of the returned `modules` list when `len(parts) == 1`, so `folder_project.html`'s module table hides the typed area too. | Invariants → test-run hidden | `F06_05c_list_folder_filter.py` (moved from `p2_s2`, storage half) + `../feature-07/F07_02b_project_view_filters_test_run.py` (moved from `p2_2c` during feature-07 Step 2; HTML half) | covered |
| SR1 | `base.html` does `{% include "tree.html" %}` so first paint is fully populated server-side; HTMX is NOT on the critical path for first render. `#tree-pane`'s `hx-get` fires only on subsequent `sse:change` events. | Invariants → Server-side initial render | `F06_06_server_side_initial_render.py` | covered |
| SF1 | Any FS change inside the data root, surviving the watcher's filters, publishes one `"change"` event after the debounce window. (Tree-pane-frame: the wired path from FS → bus → `sse:change` exists.) | Invariants → SSE-driven refresh | `F06_07_sse_refresh.py` (tree-pane wiring half) + `F06_11_acceptance.py` AC2 (end-to-end) + `F03_06_acceptance.py` AC2 / `F04_08_acceptance.py` AC6b / `F05_11_acceptance.py` AC7b (upstream cascade) | covered |
| SF2 | Every connected tab swaps `/ui/tree` into `#tree-pane` and invokes `tmsRestoreTreeState()`. (Hybrid-checkable as `#tree-pane`'s `hx-trigger="sse:change"` + the `htmx:afterSwap` hook to `tmsRestoreTreeState`.) | Invariants → SSE-driven refresh | `F06_07_sse_refresh.py` (Hybrid: static afterSwap + render-and-grep hx-trigger) | covered |
| SF3 | The **writing tab** does NOT receive the event (covered by `_mark_write` in `02-storage-core` + the watcher's `was_recently_written` filter in `03-watcher-and-sse`). | Invariants → SSE-driven refresh | `F06_07_sse_refresh.py` (tree-pane restatement: no bespoke bypass) + `F02_06_self_write.py` + `F03_01_event_filtering.py` EF3 + `F03_06_acceptance.py` AC1 + `F04_08_acceptance.py` AC6a + `F05_11_acceptance.py` AC7a (upstream cascade) | covered |
| MR1 | The manual refresh button (`↻`) is rendered inside `tree.html` itself, so every swap re-renders the button (stateless). | Invariants → Manual refresh button | `F06_08_manual_refresh.py` | covered |
| MR2 | The refresh button is pure HTMX: `hx-get="/ui/tree" hx-target="#tree-pane" hx-swap="innerHTML"`. No JS. | Invariants → Manual refresh button | `F06_08_manual_refresh.py` | covered |
| MR3 | The refresh button carries `aria-label="Refresh tree"` and a `title` attribute for accessibility. | Invariants → Manual refresh button | `F06_08_manual_refresh.py` | covered |
| CN1 | Folder caret `<button>`: `onclick="event.stopPropagation(); toggleTreeFolder(...)"`. Does NOT carry `hx-*` attributes (no HTMX navigation triggered). | Invariants → Click navigation | `F06_09_click_navigation.py` | covered |
| CN2 | Folder name `<span>`: `hx-get="/ui/folder/<path>" hx-target="#main-pane" hx-swap="innerHTML"`. Works at any depth (depth-0 / 1 / 2..MAX_FOLDER_DEPTH). | Invariants → Click navigation | `F06_09_click_navigation.py` (tested at depths 1, 2, 3, 5) | covered |
| CN3 | File rows (both `.tree-file` and `.tree-other`): `hx-get="/ui/file/<path>"` → `#main-pane`. The route maps non-`.feature` paths to `unsupported.html`. | Invariants → Click navigation | `F06_09_click_navigation.py` (HTML + route round-trip) | covered |
| EP1 | Toggling the caret mutates `tmsExpandedFolders` (add on expand, delete on collapse). (Same as CS2 from the state-mutation angle; this row's primary frame is the toggle-roundtrip behaviour.) | Invariants → Expanded-state preservation | `F06_10_expanded_state.py` (Hybrid: static `if (isHidden) delete; else add` + render-and-grep onclick) | covered |
| EP2 | `htmx:afterSwap` on `#tree-pane` runs `tmsRestoreTreeState()`, which walks `[data-path]` rows and re-expands any path in the Set. (Static-checkable as the body listener wiring + `tmsRestoreTreeState`'s loop body.) | Invariants → Expanded-state preservation | `F06_10_expanded_state.py` (Hybrid: static body + DOM-parse data-path) | covered |
| EP3 | Folders that disappeared between renders simply drop off — `tmsRestoreTreeState()` only re-applies to rows still present in the DOM (no exception on missing path). (Static-checkable as the `if (!path \|\| !…has(path)) return` guard.) | Invariants → Expanded-state preservation | `F06_10_expanded_state.py` (static guard pattern check) | covered |
| AC1 | First paint of the page shows the tree fully populated without any HTMX request having fired. (Single `GET /` response carries all tree HTML; no out-of-band `/ui/tree` needed.) | Acceptance criteria | `F06_11_acceptance.py` | covered |
| AC2 | Out-of-band edits cause exactly one `/ui/tree` swap per debounced burst on every open tab. End-to-end claim (Q2 sign-off): subscribe to the bus, fire external FS burst, assert exactly one `"change"` per subscriber after `DEBOUNCE_SECONDS * 0.9`, then independently `GET /ui/tree` (the HTMX-would-do GET on `sse:change`) and assert the response reflects the new FS state. | Acceptance criteria | `F06_11_acceptance.py` (end-to-end) + `F03_06_acceptance.py` AC2 / `F04_08_acceptance.py` AC6b / `F05_11_acceptance.py` AC7b (upstream cascade) | covered |
| AC3 | Expanding a folder, then triggering an external change, leaves that folder still expanded after the refresh. (Strengthens EP1 + EP2 end-to-end.) | Acceptance criteria | `F06_11_acceptance.py` (Hybrid: static module-scope Set + afterSwap wiring + render-and-grep data-path) | covered |
| AC4 | Clicking the `↻` refresh button issues exactly one `GET /ui/tree` and re-applies the expanded state. (Strengthens MR2 + EP2.) | Acceptance criteria | `F06_11_acceptance.py` | covered |
| AC5 | Clicking a folder name navigates the main pane; clicking the caret does NOT. (Strengthens CN1 + CN2.) | Acceptance criteria | `F06_11_acceptance.py` | covered |
| AC6 | Clicking a `.feature` file row loads the file editor; clicking a non-feature file row loads `unsupported.html`. (Strengthens CN3 + the route's `_is_feature_path` branch.) | Acceptance criteria | `F06_11_acceptance.py` | covered |

## Summary

- Total rules: **31** (4 template, 1 route, 3 wiring, 3 client state, 3 test-run hidden, 1 server-side initial render, 3 SSE-driven refresh, 3 manual refresh, 3 click navigation, 3 expanded-state, 6 acceptance).
- `covered`: **31**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-06 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 06`
exits zero with all **14 smokes** green — 10 new + 4
moved-and-refined). The 4 previously `partial` rows post
Step 2 (WR3, SF1, SF3, AC2) flipped to `covered` via
tree-pane-frame additions in F06_03 / F06_07 / F06_11
(SF1 + AC2 share the F06_11 end-to-end test).

## Notes & flags

- **Step 2 plan (move four `p2_*` smokes into
  `feature-06/`).** Per Q3 sign-off ("keep the
  restructure approach, move relevant test parts to
  `feature-06/`"):
  - `p2_s1_list_tree_hides_test_run.py` →
    `F06_05a_list_tree_filter.py` (HD1 storage half).
  - `p2_2b_tree_hides_test_run.py` →
    `F06_05b_tree_html_filter.py` (HD1 HTML half).
  - `p2_s2_list_folder_hides_test_run.py` →
    `F06_05c_list_folder_filter.py` (HD3 storage half).
  - `p2_s5_deep_test_run_not_treated_as_typed_area.py`
    → `F06_05d_depth3_allowed.py` (HD2 both halves
    after Step-3 refine).
  - **Originally stayed in `.smoke-scratch/` root** (NOT
    moved by feature-06 — *superseded*: all of these were
    subsequently folded into `feature-*/` by later cycles;
    see each owner's Step logs):
    - `p2_2c_project_view_hides_test_run.py` —
      primary frame = feature-07 (`folder_project.html`
      module table); HD3 HTML-half incidental.
    - `p2_2h` → `feature-10/F10_81_test_run_lazy_mount.py` /
      `p2_s7` → `feature-10/F10_79_sidebar_shell_renders.py`
      — primary frame = feature-10 (sidebar shell + lazy
      mount; folded in feature-10 Step 5).
    - `p2_2a` → `feature-10/F10_80_tab_strip_initial_state.py`
      (Step 5) / `p2_2d` / `p2_2e` / `p2_s3` / `p2_s4`
      / `p2_s6` — primary frame = feature-10
      (test-run sidebar + SSE behaviour; moved into
      feature-10 during its own cycle).
- **Step 3 plan (refine moved files).** Each moved
  file gets:
  - Updated docstring naming the new `F06_05<x>` ID
    and the spec rule (HD1/HD2/HD3).
  - Added positive-control assertions ("`Checkout`
    IS in the listing") alongside the existing
    negative invariants ("`test-run` is NOT in the
    listing"), per the assertion-message discipline
    from features 02–05.
  - For `F06_05d`, extend with a `/ui/tree` HTML half
    asserting that a depth-3 `test-run/` row is
    actually rendered (depth-3 IS visible — the
    spec's positive invariant). This is the only
    moved-file delta that adds new assertions.
  - For `F06_05b`, add a positive-control assertion
    that the project's name and the typed-area's
    sibling module both appear in the HTML, plus
    confirm no `<aside>` is needed in the response
    (the partial is just a `<div>` tree).
- **Q1 — Hybrid JS approach.** EP1 / EP2 / EP3 / CS2
  / CS3 / AC3 each use a Hybrid test:
  - **Static** half: regex over `app/static/app.js`
    source text — assert the function body has the
    expected structural shape (Set add/delete on the
    right branches; the `if (!path \|\| !…has(path))
    return` guard; the `document.body
    .addEventListener("htmx:afterSwap", ...)` block
    that targets `#tree-pane`).
  - **Render-and-grep** half: hit `/` (base.html) and
    `/ui/tree` with the Flask test client and grep
    the response HTML for the wiring (caret
    `onclick="… toggleTreeFolder(…)"`; `data-path`
    attribute presence on every folder row;
    `hx-trigger="sse:change"` on `#tree-pane`).
  - **DOM-parse** half: `re.findall` extracts the
    `data-path="..."` attributes from the response
    HTML and asserts the tree shape (depths,
    parent-child relations). This is the same
    approach as feature-04 / feature-05 UI* smokes
    but extended per Q1.
- **Q2 — End-to-end AC2 claim.** `F06_11_acceptance.py`
  AC2 spins up `create_app()` with the watcher started,
  subscribes two queues to the bus directly
  (`app.extensions["bus"].subscribe()`), fires an
  external FS burst that bypasses `Storage`, asserts
  each subscriber receives exactly one `"change"` event
  no sooner than `DEBOUNCE_SECONDS * 0.9` after the
  last write, AND then independently issues
  `GET /ui/tree` (simulating what HTMX would do on
  `sse:change`) and asserts the response reflects the
  new FS state (the new file's leaf name + path appears
  in the HTML).
- **SF2 ("every connected tab swaps")** is
  Hybrid-tested in `F06_07_sse_refresh.py`: the
  base.html grep finds `<aside id="tree-pane">` with
  `hx-trigger="sse:change"`; the app.js grep finds
  the `htmx:afterSwap` listener that routes to
  `tmsRestoreTreeState()`. Together these prove every
  connected tab will swap on `sse:change` (modulo
  HTMX library behaviour, which AC2 covers
  end-to-end).
- **MR3 accessibility check.** Spec mandates
  `aria-label="Refresh tree"` AND a `title` attribute
  on the refresh button. `F06_08_manual_refresh.py`
  greps for both attribute strings in the `/ui/tree`
  response HTML, catching both omissions independently.
- **Spec gaps discovered during Step-1 read-through.**
  - `tree.html` carries TWO doc-comments referencing
    legacy "Do step 13/14 lands; for now the click is
    pure toggle" — both are stale (those steps
    shipped). Not a behavioural gap; flag for
    spec/template comment cleanup. Smoke does NOT
    assert on these (they're documentation noise).
  - SF3's "writing tab does NOT receive the event"
    is the same suppression contract as feature-04
    AC6 / feature-05 AC7. Those were split into
    a/b sub-rules; feature-06 doesn't need an SF3
    split because the spec already cleanly separates
    SF1 (publish) from SF3 (suppress).

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-06:

0. **NEW top-level rule (applies to all subsequent
   features).** *"Split tests into smaller parts if
   the content and scope are long (normally more than
   90 LOC)."* Memorialised as a soft guideline (NOT a
   hard limit): trigger to split when the file's
   failure messages would become ambiguous about which
   rule failed; do not retroactively split features
   01–05. Applies to feature-06's `F06_05<x>` split
   above and to future features' planning.
1. **Q1 — JS-runtime testable shape.** Approved (b)
   **Hybrid**: static for function bodies +
   render-and-grep for `htmx:afterSwap` wiring +
   DOM-parse for tree shape. EP1 / EP2 / EP3 / CS2 /
   CS3 / AC3 use this.
2. **Q2 — AC2 testable shape.** Approved
   **end-to-end claim**: subscribe to bus, fire
   external FS burst, assert one `"change"` per
   subscriber, AND independently `GET /ui/tree` to
   verify the swap target reflects new FS state.
3. **Q3 — Restructure approach.** Approved: move four
   `p2_*` smokes (`p2_s1`, `p2_2b`, `p2_s2`, `p2_s5`)
   into `feature-06/` with `F06_05<a-d>` IDs. Apply
   the same primary-frame-driven restructure to
   subsequent features.
4. **Q4 — partial count refinement.** After Step 2's
   moves, HD1/HD2/HD3 flip from `partial` to
   `covered`. Pre-Step-4 status: covered=3,
   partial=4 (WR3, SF1, SF3, AC2), missing=24.

Once Step 2 + Step 3 land, Step 4 writes the remaining
`F06_*.py` files to cover the 24 `missing` rows and
the 4 `partial` rows' tree-pane-frame halves.

## Step 2 / Step 3 execution log

**Jun 8, 2026** — Step 2 (Restructure) + Step 3 (Refine)
executed for feature-06:

- Step 2 moves (4 files, via `git mv` to preserve
  history):
  - `.smoke-scratch/p2_s1_list_tree_hides_test_run.py`
    → `.smoke-scratch/feature-06/F06_05a_list_tree_filter.py`
  - `.smoke-scratch/p2_2b_tree_hides_test_run.py`
    → `.smoke-scratch/feature-06/F06_05b_tree_html_filter.py`
  - `.smoke-scratch/p2_s2_list_folder_hides_test_run.py`
    → `.smoke-scratch/feature-06/F06_05c_list_folder_filter.py`
  - `.smoke-scratch/p2_s5_deep_test_run_not_treated_as_typed_area.py`
    → `.smoke-scratch/feature-06/F06_05d_depth3_allowed.py`
- Step 3 refinements per moved file:
  - **F06_05a**: docstring anchored to HD1 + spec
    section; spec-anchored failure messages; positive
    control (sibling module 'Checkout' must appear).
  - **F06_05b**: HTML-half framing; positive controls
    (project name 'Alpha' + sibling module's
    `data-path` must appear); strengthened negative
    invariant naming the exact `data-path` prefix.
  - **F06_05c**: HD3 anchor; cross-pointer to
    `p2_2c` (the HTML half whose primary frame stays
    in feature-07); positive + negative invariants.
  - **F06_05d**: HD2 anchor; **extended with the
    HTML half** — confirms `/ui/tree` HTML carries
    `data-path="Alpha/Checkout/test-run"` for the
    depth-3 folder (the spec's positive invariant
    "depth 3 is NOT filtered" was previously only
    storage-side-tested).

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-06:

- Ten new smoke files written, one per uncovered spec
  section, ~50–220 LOC each (within the soft 90-LOC
  guideline for most; F06_04 and F06_10 sit at
  ~120–130 LOC because the Hybrid approach naturally
  adds the static + render-and-grep halves to each
  rule):
  - `F06_01_template.py` covers TM1–TM4 (4 rules).
  - `F06_02_route.py` covers RT1 (1 rule; empty-state
    + populated branches).
  - `F06_03_wiring.py` covers WR1–WR3 (3 rules).
  - `F06_04_client_state.py` covers CS1–CS3 (3 rules,
    Hybrid: static body + render-and-grep onclick +
    DOM-parse data-path).
  - `F06_06_server_side_initial_render.py` covers SR1
    (3 sub-claims: populated branch, empty branch,
    SSE wiring still present).
  - `F06_07_sse_refresh.py` covers SF1–SF3 (Hybrid:
    static afterSwap wiring + render-and-grep
    hx-trigger + cascade refs to feature-02/03/04/05).
  - `F06_08_manual_refresh.py` covers MR1–MR3
    (re-render stability, pure-HTMX wiring,
    accessibility attributes).
  - `F06_09_click_navigation.py` covers CN1–CN3
    (caret stopPropagation; folder hx-get at depths
    1/2/3/5; `.tree-file`/`.tree-other` route
    round-trip to `unsupported.html`).
  - `F06_10_expanded_state.py` covers EP1–EP3 (Hybrid:
    static `if (isHidden) delete; else add` shape +
    render-and-grep onclick + DOM-parse + static guard
    pattern).
  - `F06_11_acceptance.py` covers AC1–AC6 with AC2
    **end-to-end** (per Q2 sign-off): subscribe to the
    bus, fire external FS burst, assert one `"change"`
    per subscriber after `DEBOUNCE_SECONDS * 0.9`,
    independently `GET /ui/tree` and confirm the
    response reflects the new FS state.
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- **`run.py` regex extension.** The locked filename regex
  `^F\d+_\d+_.+\.py$` rejected the `F06_05a` suffix
  variant; extended to `^F\d+_\d+[a-z]?_.+\.py$` to
  accept the optional letter suffix used by the
  HD-split sub-files. Minimal one-character regex
  patch; surfaces in `.smoke-scratch/run.py:24`.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 06 --verbose` reports `14/14 passed; 0
  failed` and every direct rule-level `PASS <id>: ...`
  line fires.
- Full-suite re-run (`run.py` without filter) reports
  `52/52 passed; 0 failed`, confirming no regression
  in features 01 / 02 / 03 / 04 / 05.
- **Per-rule notes:**
  - **TM1–TM4** use a single fixture FS (project +
    module + .feature + sibling .txt that bypasses
    `_normalize_filename`'s reject via direct
    `pathlib` write) so all four template branches
    render in one `/ui/tree` HTML payload.
  - **RT1** exercises both the empty-state (`No
    projects yet.` placeholder) and the populated
    branch (multi-project + multi-module fixture).
  - **WR3** uses `html.find(...)` index arithmetic
    (not regex) to assert `<aside id="tree-pane">`
    precedes `<aside id="test-run-pane">` inside the
    `#sidebar-panels` wrapper. Regex would need
    balanced-paren matching across multiple sibling
    divs in `base.html`'s sidebar block.
  - **CS2** asserts the EP1 direction lock via the
    regex `if (isHidden) tmsExpandedFolders.delete(path)`
    — catches accidental sign-flips on the Set
    mutation.
  - **CS3** asserts the htmx:afterSwap wiring with a
    multi-line regex spanning the listener
    declaration through the call to
    `tmsRestoreTreeState()`. Same regex reused in
    F06_07 SF2 and F06_10 EP2 (each frames the same
    code from a different rule's angle).
  - **MR1** proves *stateless re-render* by issuing
    two consecutive `/ui/tree` fetches and asserting
    byte-identical refresh-button markup.
  - **CN2** walks parent depths 1, 2, 3, 5 to prove
    "works at any depth".
  - **CN3** completes the round-trip: not only does
    `.tree-other` have the right `hx-get`, but actually
    `GET /ui/file/<non-feature>` resolves to a body
    containing 'unsupported' / 'not supported'.
  - **EP1–EP3** share static surface with CS2/CS3 but
    re-frame the assertions around the
    *state-preservation-across-re-renders* angle.
    The two files do NOT duplicate identical assertions;
    each picks a different lens (function body shape
    vs Set survival semantics).
  - **AC2 (end-to-end)** uses two subscribers + an
    external `(target_dir / f"ext_{i}.feature").write_text(...)`
    burst of 3 writes, then independently issues `GET
    /ui/tree` and asserts all three new files'
    `data-path` attributes appear. The full pipeline
    (FS → watcher → debounce → bus → subscriber →
    HTMX-would-do GET) is exercised end-to-end.
  - **AC4** asserts one-fetch-per-click by checking
    the button is pure HTMX (no `onclick` that could
    re-fire) + that GET /ui/tree returns the partial.
    The "re-applies expanded state" half delegates to
    AC3's wiring chain (Set is module-scope +
    afterSwap calls tmsRestoreTreeState).
  - **AC5** uses belt-and-braces: caret has
    onclick+stopPropagation+toggleTreeFolder AND no
    `hx-*`; folder name has hx-get AND does NOT
    invoke `toggleTreeFolder`.
  - **AC6** does a full round-trip on `/ui/file/<p>`
    for both branches (`.feature` -> contains
    `file-editor`; `.txt` -> contains 'unsupported').

**Feature-06 cycle complete.** Per the locked plan,
**feature-07 is next** — audit
`specs/features/07-*-NEW.md` (folder views).

## Condition-coverage gap-closer (Jun 9, 2026)

`F06_12_listing_hides_temp_file.py` closes condition-coverage gap
"Pattern B": `TEMP_FILE_RE` was exercised for the boot sweep
(`F02_03` AW4) and the watcher (`F03_01` EF2), but the
`TEMP_FILE_RE.match(name)` leg of the **listing** filters in
`Storage._tree_children` (list_tree) and `Storage.list_folder` was
never driven — no smoke had placed a temp-named file inside a listed
directory. This drops an atomic-write-style temp
(`real.feature.tmp.<pid>.<hex>`) into a module *after* boot (so the
orphan sweep can't remove it) and asserts both `list_tree()` and
`list_folder()` omit it while the real `.feature` sibling survives.
No new spec rule — hardens the HD-family listing invariants.
(feature-06 now 15 smokes.)
