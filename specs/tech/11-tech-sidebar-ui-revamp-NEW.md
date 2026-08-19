# 11 · Sidebar UI revamp (Mintlify-style restyle)

_Tech spec. Filed Jun 19, 2026 (Investigate phase). First slice of a larger_
_"polish UI / enhance UX" initiative (branch `feature/revamp-ui`). Scope is_
_a **presentational restyle** of the sidebar + a shared visual foundation —_
_no data-model, on-disk, or HTTP-contract change, and **no change** to the_
_sidebar's tab / lazy-mount / SSE / deep-link / resize architecture. Grounded_
_against live code Jun 19, 2026; each touch-point below carries a file:line_
_pointer. The remaining UX themes (feedback layer, app-wide icons,_
_accessibility) are listed under § Surface for follow-up as later slices._

## Summary

Bring the sidebar toward the reference Mintlify aesthetic — an **emerald
accent**, **icons on every nav item**, soft **rounded active-pill** highlight,
and a **current-item highlight** — while preserving every structural hook and
behaviour. This is path **2a** from the investigation ("restyle, keep
architecture"); the alternative **2b** (flatten the four tabs into one grouped
nav) was rejected as high-risk because it would rewrite the lazy-mount, SSE
fan-out, and tech-10 deep-link rehydration, and reverse a documented perf
decision.

We also lay a tiny **shared visual foundation** (Tier-1): an emerald accent
adopted via Tailwind utilities, a couple of component classes in `app.css`,
and a reusable **inlined-SVG icon macro**. These are consumed by this slice and
reused by every follow-up slice.

## Scope

In scope:

- Sidebar **tab strip** restyle: vertical-rotated text buttons → horizontal
  **icon + label** buttons with an emerald active-pill.
- Sidebar **panel** restyle (all four partials): section headers, action
  buttons, tree rows (carets → chevrons, bullets → file/run/report icons,
  themed hover + rounding).
- **Current-item highlight**: mark the tree/list row matching the open
  main-pane item (wires up the currently-dormant `active_path` plumbing).
- **Collapsed-state** look adjusted to suit the new icon tabs.
- Shared **Tier-1 foundation**: emerald accent utilities, `app.css` component
  classes, an inlined-Lucide-SVG Jinja macro.
- Smoke updates for the restyle (see plan).

Out of scope (later slices / not this spec):

- Any change to sidebar **behaviour** — tab switching, lazy mount, SSE
  refresh, deep-link rehydration, resize, collapse persistence logic.
- The 2b grouped-nav information architecture.
- Feedback layer (toasts / styled confirms), app-wide icon rollout beyond the
  sidebar + header, accessibility sweep — tracked as follow-up.
- Data-model, on-disk, or HTTP-contract changes; `RUN_RESULTS`; the watcher /
  SSE pipeline.
- Precompiling Tailwind (the CDN/no-build pillar, `PLAN.md §3`, is unchanged).

## Current state (grounded)

- The Tailwind **v4 browser build** is loaded at `app/templates/base.html:8`
  (no build step). It ships the **full default palette**, so emerald accent
  utilities (`text-emerald-600`, `bg-emerald-50`, `ring-emerald-500`) work with
  **no config**. `app/static/app.css` holds only the run-status palette.
- The sidebar shell is a **36px vertical-rotated tab strip** (`#sidebar-tabs`,
  `writing-mode: vertical-rl`) + four absolutely-positioned panes
  (`tree` / `test-run` / `reports` / `enums`), at `app/templates/base.html:86-153`.
- Tab active/inactive styling and pane `.hidden` toggling live in
  `app/static/02_sidebar.js:28-54`; lazy mount in `:66-112`; collapse in
  `:207-238`.
- Tree rows + carets are in `app/templates/tree.html`,
  `app/templates/test_run_sidebar.html`, `app/templates/reports_sidebar.html`
  (all three share the recursive `.tree-folder` / `.tree-file` markup with
  glyph carets `▶/▼` and middot bullets); `app/templates/enums_sidebar.html`
  is a flat project list (no carets). Caret glyphs are also written from JS at
  `app/static/01_tree.js:20` and `:43`.
- **No current-item highlight exists today.** `window.TMS_ACTIVE_PATH` is
  declared at `app/templates/base.html:174` but **never consumed**, and
  `app/server/_shared.py` `maybe_shell` does not pass `active_path` — dead
  plumbing this slice will activate.

## Mechanism decisions

- **D1 — Accent without config.** Use Tailwind's built-in `emerald` utilities
  for the accent; add only a small set of component classes in `app/static/app.css`
  (`.tms-active-row`, focus-ring helper) where a utility string would be
  repeated across templates and JS. No Tailwind config, no build.
- **D2 — Icons via an inlined-SVG Jinja macro.** Partials re-render on every
  `sse:change` swap, so a CDN `lucide.createIcons()` approach would need
  re-initialisation after each swap (flash + wiring). Instead, add a Jinja macro
  (e.g. `app/templates/_partials/icons.html`) that emits inlined Lucide SVG by
  name; server-rendered, zero-dependency, swap-safe. JS-inserted icons (the
  collapse control) use small inline SVG strings.
- **D3 — Carets via CSS rotation, not glyph-swap.** Render one chevron SVG per
  folder row and toggle a `rotate-90` class on expand/collapse instead of
  rewriting `innerHTML` glyphs. `app/static/01_tree.js:20,43` switch from
  glyph writes to class toggles; the `.caret` hook is preserved.
- **D4 — Current-item highlight reuses the expand-state pattern.** `maybe_shell`
  passes `active_path`; a new `tmsApplyActiveRow(root)` helper (mirroring
  `tmsApplyTreeExpansion` in `app/static/01_tree.js`) applies a `.tms-active-row`
  class to the row whose `data-path` / `data-project` matches
  `window.TMS_ACTIVE_PATH`, re-applied on `htmx:afterSwap` (and at boot) so it
  survives SSE re-renders. Highlight is applied **client-side** because the
  typed-tree partials are fetched from their own `/ui/*-tree` endpoints that do
  not know the active item.

## Must-preserve structural hooks

Restyle changes **visual** classes only; these structural classes / attributes
are JS contracts and must remain:

- `.sidebar-tab` + `data-sidebar-tab` (`app/static/02_sidebar.js:28-29`).
- `.tree-folder` / `.tree-children` / `.caret` / `.tree-file`
  (`app/static/01_tree.js`, all sidebar partials).
- `data-path` / `data-depth` / `data-project` row attributes.
- The four pane ids (`tree-pane` / `test-run-pane` / `reports-pane` /
  `enums-pane`) + their `hx-*` wiring + the `08_enums_manager.js`-before-
  `09_bootstrap.js` script order.

## Affects

- **`app/templates/base.html`** — tab strip markup, collapse icon, and the
  `active_path` consumption; the most visible change.
- **`app/static/02_sidebar.js`** — active-class toggles (`:28-45`) and the
  collapsed-state appearance (`:207-238`); behaviour unchanged.
- **`app/static/01_tree.js`** — caret glyph writes → rotation-class toggles;
  new `tmsApplyActiveRow` helper.
- **`app/static/09_bootstrap.js`** — call `tmsApplyActiveRow` from the existing
  `htmx:afterSwap` handler and at boot (alongside the expand-state restore).
- **`app/server/_shared.py`** — `maybe_shell` now passes `active_path` to the
  shell render.
- **The four sidebar partials** (`tree.html`, `test_run_sidebar.html`,
  `reports_sidebar.html`, `enums_sidebar.html`) — headers, rows, icons.
- **`app/static/app.css`** — accent/component classes + active-row style.
- **`.smoke-scratch/feature-10/F10_80_tab_strip_initial_state.py`** — asserts
  the literal active/inactive tab classes; must be updated to the new classes.

## Depends on

- **Tailwind v4 browser build** (`app/templates/base.html:8`) shipping the full
  default palette — the accent relies on built-in `emerald` utilities.
- **The sidebar architecture** (tabs / lazy mount / SSE refresh / deep-link
  rehydration / resize) staying as-is — this slice restyles around it, not
  through it.
- **The JS structural hooks** listed above remaining the contract between
  templates and `01_tree.js` / `02_sidebar.js`.
- **tech-10** deep-link rehydration (`active_tab` / `expand_paths`) — unchanged;
  this slice only additionally consumes `active_path`.

## Surface for follow-up

- **Makes easier:** the Tier-1 foundation (accent utilities, component classes,
  the icon macro) is reused verbatim by later slices — **Theme A** (toasts +
  styled confirm modal to replace the ~8 `window.confirm` sites; note the
  `beforeunload` guard at `app/static/09_bootstrap.js:150` must stay a
  synchronous native confirm), **app-wide icon rollout**, and the
  **accessibility sweep** (roles / `aria-*` / focus-visible on tabs + dialogs).
- **Makes easier:** the `active_path` plumbing, once live, can drive
  breadcrumb / title context elsewhere.
- **Makes harder / watch:** any future styling smoke should assert on
  **structural hooks** (data-attributes, ids) rather than literal utility
  classes, to avoid the F10_80-style brittleness this slice has to repair.
- **Deferred:** the 2b grouped-nav IA remains possible as a later, riskier
  initiative built on top of this restyle.

## Acceptance criteria

- The sidebar renders with emerald accent, icon + label tabs, an emerald
  active-pill on the selected tab, chevron carets, and per-type row icons; the
  open item's row is visibly highlighted and the highlight survives an SSE
  re-render.
- All sidebar **behaviour is unchanged**: tab switch, lazy mount of typed panes,
  background SSE refresh, deep-link rehydration (cold load to a deep-linked
  item still expands + activates the right tab), drag-resize, and
  collapse/restore (with persistence) all work as before.
- Collapsing the sidebar shows a clean icon rail and restores to the prior
  width on expand.
- The full smoke suite is green, including the **updated** F10_80 and a **new**
  smoke covering the active-row highlight; a manual browser pass confirms the
  visuals (no Playwright — tech-01 R7).

---

## Temporary implementation plan (delete on ship)

Detailed, ordered actions. Each step states a **verify** check (AGENTS.md §4).
Keep the suite green between steps; this is a single-branch (`feature/revamp-ui`)
effort, so commit per step for easy revert.

### Step 0 — Tier-1 foundation
1. Add to `app/static/app.css`: `.tms-active-row` (emerald-50 bg, emerald-700
   text, rounded) and a focus-ring helper. → **verify:** classes resolve in the
   browser; no console errors.
2. Create `app/templates/_partials/icons.html` with a Jinja macro
   `icon(name, classes='')` emitting inlined Lucide SVGs for the names this
   slice needs: `folder`, `file-text`, `play`, `bar-chart-2`, `tags`,
   `chevron-right`, `chevrons-left`, `refresh-cw`, `plus`. → **verify:** macro
   imports and renders a valid `<svg>` in a scratch template.

### Step 1 — Tab strip (base.html + 02_sidebar.js)
3. In `app/templates/base.html:86-123`, replace the four vertical-rotated text
   buttons with horizontal **icon + label** buttons (drop `writing-mode`); keep
   `data-sidebar-tab`, `.sidebar-tab`, the `onclick` wiring, ids, and order.
   Default-active = `tree`. Replace the collapse glyph at `:93` with an icon.
4. In `app/static/02_sidebar.js:28-45`, swap the active/inactive class sets
   (`border-slate-800` / `font-medium` / `text-slate-800` ↔ `border-transparent`
   / `text-slate-500`) for the new emerald active-pill / muted-inactive classes.
5. In `app/static/02_sidebar.js:207-238`, adjust the collapsed look to an
   icon-only rail (icons remain visible/clickable when collapsed); keep the
   width + persistence logic untouched.
   → **verify (steps 3-5):** tabs switch correctly; active tab shows the pill;
   collapse/expand + persisted width still work; no behaviour regression.

### Step 2 — Panel partials
6. Restyle the headers in `tree.html`, `test_run_sidebar.html`,
   `reports_sidebar.html`, `enums_sidebar.html` (label + action buttons:
   `+ New run` / `+ New report` / refresh) using the icon macro + accent.
7. In the three tree partials, replace glyph carets with the `chevron-right`
   icon (rotatable) and middot bullets with type icons (`file-text` for
   features, `play` for runs, `file-text` + the existing type badge for
   reports); add themed hover + rounding to rows. `enums_sidebar.html` rows get
   the project icon + themed hover.
   → **verify:** all four panels render; folder rows still toggle; nav clicks
   still load the main pane.

### Step 3 — Caret rotation (01_tree.js)
8. In `app/static/01_tree.js:20` (`toggleTreeFolder`) and `:43`
   (`tmsApplyTreeExpansion`), replace the `innerHTML` glyph writes with toggling
   a `rotate-90` class on the `.caret` element.
   → **verify:** expand/collapse rotates the chevron; SSE re-render preserves the
   expanded/rotated state.

### Step 4 — Current-item highlight
9. In `app/server/_shared.py`, have `maybe_shell` compute + pass `active_path`
   (the open item's data-root-relative path) to the shell render so
   `window.TMS_ACTIVE_PATH` is populated.
10. Add `tmsApplyActiveRow(root)` to `app/static/01_tree.js` (mirroring
    `tmsApplyTreeExpansion`): add `.tms-active-row` to the row whose `data-path`
    / `data-project` equals `window.TMS_ACTIVE_PATH`, clearing any previous.
11. Call `tmsApplyActiveRow` from the `htmx:afterSwap` handler in
    `app/static/09_bootstrap.js:5-18` (for each sidebar pane) and once in
    `tmsBootShell` (`:119-140`).
    → **verify:** deep-linking to an item highlights its row; the highlight
    survives an SSE re-render and a tab switch.

### Step 5 — Tests + manual pass
12. Update `.smoke-scratch/feature-10/F10_80_tab_strip_initial_state.py` to
    assert the **new** active/inactive tab classes (and keep the
    `tmsToggleSidebarCollapse` / `tmsStartSidebarResize` / `tmsSwitchSidebarTab`
    presence checks). Sweep `feature-10/F10_8*` for any sibling tab-strip class
    assertions and update in kind.
13. Add a smoke `F11_xx_active_row.py` asserting `active_path` reaches the shell
    (`window.TMS_ACTIVE_PATH` populated) and that `tmsApplyActiveRow` is wired
    in `09_bootstrap.js`.
14. Confirm the safe smokes still pass untouched: `feature-06/F06_03_wiring`,
    `feature-12/F12_24_js_wiring`, `feature-13/F13_15_tab_and_sse_wiring`.
    → **verify:** full smoke suite green; manual browser pass over all four
    tabs + collapse + deep-link.
