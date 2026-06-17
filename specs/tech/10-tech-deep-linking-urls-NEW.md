# 10 · Deep-linkable URLs + browser history for main-pane items

_Status: **COMPLETE** (shipped Jun 17, 2026). Investigate-first
item promoted from `IN-PROGRESS.md`. Scope chosen by USER: **full
content-negotiation + active-tab restore + directory-tree auto-expand**.
Approach locked to **Option 1** (OQ1 + OQ2 resolved — see below): reuse the
existing `/ui/...` paths as the visible URL, and ship the native
`beforeunload` dirty-prompt only (defer the in-app `popstate` confirm).
Spike completed (Jun 16, 2026) — see **Spike results**; D2 upgraded to a
full-reload restore. Built in **phases 10a → 10b → 10c** (see **Phasing**).
**tech-10 COMPLETE Jun 17, 2026** — phases 10a + 10b + 10c all shipped (suite
317/317; 10a browser-verified). The two optional 10c niceties (SPA-snappy
restore, clean public URLs) were closed **won't-do** (see Phasing 10c). The
negotiation signal is `Sec-Fetch-Mode: navigate` (see D1 as-built refinement)._

## Scope

Make the open **main-pane item** reflected in the browser address bar and make
**Back / Forward / Refresh / direct-link / bookmark** all restore it. Item
types + their existing `/ui/*` partial routes (`root/app/server/routes_ui.py`):

- **folder** → `/ui/folder/<path>`
- **test case** (`.feature` / other file) → `/ui/file/<path>`
- **test run** → `/ui/run/<project>/<group>/<file_name>`
- **test report** → `/ui/report/<project>/<file_name>`
- **enum** → `/ui/enums/<project>`

On a cold load (refresh / direct-link / history restore) we additionally:
- activate the **correct sidebar tab** (tree / test-run / reports / enums); and
- **auto-expand** that tab's tree down to the open item's path.

**Out of scope (v1):** deep-linking `/ui/search` results; persisting sidebar
width/collapse via URL (already localStorage); the typed-area sub-views beyond
what the item routes already render.

## Depends on / builds on

- **feature-06** (tree pane + shell): `root/app/templates/base.html`,
  `root/app/templates/tree.html`, `root/app/static/01_tree.js`
  (`tmsExpandedFolders` + `tmsRestoreTreeState`).
- **feature-10** (sidebar tabs): `root/app/static/02_sidebar.js`
  (`tmsSwitchSidebarTab` + the `tmsActivate*Pane` lazy mounts).
- Item routes in `root/app/server/routes_ui.py`; shell route `index()` in
  `root/app/__init__.py:66-74`.

## Current state (grounded)

- **Shell never reflects state.** `index()` renders `base.html`; the
  `#main-pane` (`root/app/templates/base.html:161-164`) is hardcoded to
  `hx-get="/ui/folder/" hx-trigger="load"`, so every load boots to the root
  folder. The active sidebar tab is hardcoded to **Directory** in the markup.
- **All `/ui/*` templates are bare fragments** — zero `extends` in
  `root/app/templates`. A direct GET to an item URL returns a shell-less
  fragment.
- **No `hx-push-url` anywhere.** Navigation is inline
  `hx-get="/ui/..." hx-target="#main-pane"` in `tree.html`, the folder views,
  the sidebars, breadcrumbs, and search results.
- **Editors boot via a tail `<script>`** inside their fragment (e.g.
  `tmsBootRunEditor()` in `run_editor.html`, the file editor likewise). A
  normal HTMX swap runs these; an HTMX history **snapshot** restore does **not**
  re-run scripts — so naive history caching brings editors back inert.
- **Sidebar tab + tree expand-state** are JS-only, in-session
  (`tmsSwitchSidebarTab`, `tmsExpandedFolders`); nothing rehydrates on reload.

## Spike results (Jun 16, 2026)

Server half (`root/.smoke-scratch/_investigate/deep-linking/spike_server.py`,
run against the real app):
- **Confirmed:** every `/ui/*` item route returns a **fragment** (`doctype`
  absent) **regardless** of the `HX-Request` header — there is no negotiation
  today, so it must be added.
- **Confirmed:** `base.html` **ignores** `initial_main_url` / `active_tab`
  kwargs — `#main-pane` stays hardcoded to `/ui/folder/`. The template **must**
  be parameterised.

Client half (read the pinned **htmx 2.0.10** source directly):
- `restoreHistory()` on `popstate`: with the snapshot cache disabled it takes
  the **miss** branch — `if config.refreshOnHistoryMiss → htmx.location.reload()`
  (a **full browser reload**); else it XHR-swaps the response into
  `getHistoryElement()` (default `<body>`) via `innerHTML`.
- `historyCacheSize <= 0` purges/disables the snapshot cache.
- **Key consequence:** setting `historyCacheSize = 0` **and**
  `refreshOnHistoryMiss = true` makes Back/Forward a **full page reload** — a
  plain browser GET → the shell branch → a brand-new document. This
  **eliminates the `const`-redeclaration blindspot entirely** (no
  body-`innerHTML` swap that re-inserts the bottom `<script src>` tags), and
  collapses the server contract to a single rule: **`if not HX-Request →
  shell`**. The `HX-History-Restore-Request` special-case is no longer needed.
- **Remaining real caveat (unrelated to history):** `tmsRestoreTreeState` is
  scoped to `#tree-pane` only; the test-run / reports / enums panes have **no**
  expand-restore mechanism. So D6 auto-expand for the **typed** tabs is real new
  work → split into phase **10b**.

## Phasing (scope split)

- **10a — Core deep-linking (high confidence; ship first).** Server
  negotiation (`if not HX-Request → shell`) on the 5 item routes + `index()`;
  parameterise `base.html` (`initial_main_url`, `active_tab`, `active_path`);
  `htmx.config.historyCacheSize = 0` + `refreshOnHistoryMiss = true`;
  `hx-push-url` on main-pane nav elements; active-tab restore (incl. the D4
  folder sub-path refinement); **Directory-tree** auto-expand (`#tree-pane`
  only); `beforeunload` dirty guard. Delivers: URL reflects the item;
  refresh / direct-link / bookmark / Back / Forward all restore it; correct tab;
  directory tree opens to the item.
- **10b — Typed-tab tree auto-expand. SHIPPED Jun 16, 2026.** Generalised the
  Directory-tree restore into `tmsApplyTreeExpansion(root, set)`; added a
  `tmsTypedExpand` set seeded at boot for a non-tree active tab and re-applied
  to the test-run / reports / enums panes on every `htmx:afterSwap` (lazy mount
  + SSE). Server emits the typed tree's folder `data-path` nodes — run →
  `[<p>, <p>/test-run/<g>]`, report → `[<p>]`, test-run area/group folders
  likewise. Enums has no folder depth (no-op). Tests: `tech-10/T10_07`
  (server typed expand) + `T10_08` (JS restore wiring); `F06_04`/`F06_10`
  updated for the shared-helper refactor. Suite **314/314**.
- **10c — Optional polish.** **In-app `popstate` dirty-confirm SHIPPED Jun 16,
  2026:** `09_bootstrap.js` wraps htmx's `window.onpopstate` — on a dirty
  editor it confirms, **re-pushes the editor URL on cancel** (undoing the
  popstate so the address bar matches the still-shown editor), and clears the
  dirty flag on confirm so the ensuing full-reload's `beforeunload` stays silent
  (no double prompt). `tmsCurrentEditorUrl()` reconstructs the run/file editor
  URL from its state. Test: `tech-10/T10_09`.
  - **Bad / invalid-URL handling SHIPPED Jun 16, 2026:** pasting (or deep-
    linking) a URL to a **missing item** under a valid `/ui` route returns the
    **shell** (200, so the frame + sidebar load), and the `#main-pane` HX fetch
    then 404s with the server's `_ui_error_html` snippet. Since htmx does **not**
    swap 4xx/5xx by default, a scoped `htmx:responseError` listener
    (`09_bootstrap.js`) injects that snippet into `#main-pane` (and drops stale
    editor state) so the user sees a clean message instead of a stuck
    "Loading…". Covers missing file / run / report / folder — including the
    catch-all `/ui/folder/<path>` and `/ui/file/<path>` converters; a path that
    matches **no** route at all still falls to Flask's default 404 (rare; not a
    deep link to a real item). Tests: `tech-10/T10_10` (server) + `T10_11`
    (inject wiring).
  - **Won't-do (closed Jun 17, 2026):** SPA-snappy Back/Forward
    (`hx-history-elt` content wrapper + snapshot cache) — reverses D2 and
    reintroduces the spike-identified breakage (editor tail-scripts not re-run,
    top-level `const` clobbering), and the full-reload restore isn't heavy; a
    cleaner public URL scheme — cosmetic, no demand. Reopen from here if the
    gating conditions ever materialise.

## Decisions (proposed)

- **D1 — Content-negotiation, not push-url-only.** Each item route returns the
  **fragment** by default and the **full `base.html` shell** only for a genuine
  browser **navigation**. This is what makes refresh / direct-link / bookmark
  work; a bare `hx-push-url` would 404-into-a-shell-less fragment on cold load.
  - **Signal (as-built refinement):** the shell is returned when
    `Sec-Fetch-Mode == "navigate"` (typed URL / refresh / bookmark / link /
    Back-Forward reload), **not** merely "no `HX-Request`". Rationale: dozens of
    existing smokes (and any programmatic/curl client) GET `/ui/*` **without**
    an HX header and rightly expect the **fragment** — `/ui/*` is the fragment
    endpoint for everyone except a human navigating the browser there. HTMX
    swaps additionally carry `HX-Request` (also → fragment). Verified: the full
    suite stays green with this signal; an `HX-Request`-only signal regressed
    70 fragment-GET smokes. `Sec-Fetch-Mode` is emitted by all modern browsers
    on localhost (a secure context), which is this tool's deployment.
- **D2 — History restore = full reload (upgraded after spike).** Set
  `htmx.config.historyCacheSize = 0` **and** `htmx.config.refreshOnHistoryMiss =
  true`. Per the htmx 2.0.10 source, this makes Back/Forward call
  `htmx.location.reload()` — a **full browser navigation** that hits the
  shell branch like any cold load, so scripts run once in a fresh document
  (no body-swap, **no `const`-redeclaration risk**). Because the reload is a
  real browser navigation it carries `Sec-Fetch-Mode: navigate` → the D1 shell
  branch, with no `HX-History-Restore-Request` special-case needed. Trade-off:
  Back/Forward is a full
  reload (not SPA-snappy) — acceptable for a local-first tool, and far simpler /
  more robust than snapshot restore. Unified model: **cold load == refresh ==
  Back/Forward == "render shell; the `#main-pane` load-trigger fetches the
  item"**.
- **D3 — Reuse `/ui/<...>` as the canonical address-bar URL.** Least work, and
  the route already encodes the item identity. (No separate public scheme.)
- **D4 — Active tab is derived server-side from the URL** and applied on boot:
  - `file → tree`
  - `run → test-run`
  - `report → reports`
  - `enums → enums`
  - `folder` → inspect the **sub-path**, not just the prefix (refinement):
    - `/ui/folder/<p>/test-run...` → **test-run** tab
    - `/ui/folder/<p>/report...` → **reports** tab
    - otherwise → **tree** tab

  This matters because the run-group listing views are reached via the *folder*
  route — `/ui/folder/<p>/test-run` (area) and `/ui/folder/<p>/test-run/<g>`
  (runs list) — yet `test-run/` (and `report/`) are **hidden from the directory
  tree** (`RESERVED_DEPTH2_NAMES`). A naive `folder → tree` rule would activate
  the Directory tab on a folder that isn't even in that tree. Bootstrap calls
  `tmsSwitchSidebarTab(activeTab)` (reuses the existing activate/lazy-mount
  path) instead of duplicating activation logic.

  Concrete examples (real `./project` tree):
  - `/ui/folder/demo-project/module01` → tree
  - `/ui/file/demo-project/module01/test%2000.feature` → tree
  - `/ui/folder/kchatb2b/desktop-app/UI/AI%20chat` → tree (spaces → `%20`)
  - `/ui/folder/demo-project/test-run/run-group1` → **test-run**
  - `/ui/run/demo-project/run-group1/run01.yaml` → **test-run**
  - `/ui/report/kchatb2b/report01.yaml` → **reports**
  - `/ui/enums/kchatb2b` → **enums**
- **D5 — `hx-push-url="true"` is added per nav element**, scoped to elements
  that target `#main-pane`. NOT global (a `<body>`-level inherit would wrongly
  push `/ui/tree`, `/ui/test-run-tree`, the lazy mounts, and SSE refreshes).
  Editor-internal reloads (`06_run_editor.js` `reload()` / `_reloadAndAnnounce`)
  pass `pushUrl:false` (or replace) so they don't stack history entries.
- **D6 — Tree auto-expand on cold load.** The active item's **ancestor folder
  paths** are passed to the client (`window.TMS_ACTIVE_PATH` + tab); bootstrap
  seeds `tmsExpandedFolders` with those ancestors before `tmsRestoreTreeState`
  runs, so the tree opens down to the item. Ancestor derivation per type:
  - file/folder → split the data-root-relative path on `/` (drop the leaf for a
    file; keep all segments for a folder).
  - run → `<project>`, `<project>/test-run`, `<project>/test-run/<group>` in the
    **test-run** tree.
  - report → `<project>`, `<project>/report` in the **reports** tree.
  - enums → `<project>` in the **enums** tree.

  **Spike detail (Jun 16, 2026 — Directory tree, phase 10a):**
  - `tmsRestoreTreeState` (`root/app/static/01_tree.js:30-42`) iterates **all**
    `#tree-pane .tree-folder` rows and un-hides each matching level
    independently, so seeding **every ancestor path** auto-expands to any depth
    with **no change to the restore function**.
  - **Gap:** restore is wired **only** to `htmx:afterSwap` for `#tree-pane`
    (`root/app/static/09_bootstrap.js:5-8`); on cold load the tree is a server
    `{% include %}` (not an htmx swap), so it is **never called at boot**. Fix
    (the whole change): emit `window.TMS_EXPAND_PATHS` server-side and have
    `tmsBootShell` seed `tmsExpandedFolders` + call `tmsRestoreTreeState()`
    once.
  - **Ancestor derivation** (only when `active_tab == "tree"`):
    - folder `Alpha/Mod/Sub` → `["Alpha", "Alpha/Mod", "Alpha/Mod/Sub"]`
      (prefixes **incl. self**).
    - file `Alpha/Mod/x.feature` → `["Alpha", "Alpha/Mod"]` (prefixes **excl.**
      the leaf).
    - typed `/ui/folder/<p>/test-run...` → **empty** (test-run-tab context; that
      tree is hidden from `#tree-pane`).
  - SSE refresh re-fires `afterSwap` → restore re-applies from the Set → stays
    expanded (no flicker-collapse). A later user-collapse removes the path via
    `toggleTreeFolder` (one-time seed). Active-row **highlight** is not present
    today (no selected style) — optional polish, not required.
  - Cost ≈ 15–20 LOC. Confidence ~90%.

  **Typed tabs deferred:** the test-run / reports / enums panes have **no**
  expand-restore mechanism at all → their auto-expand is phase **10b**.
- **D7 — Dirty-editor guard (`beforeunload`) is ALREADY IMPLEMENTED.** Spike
  found the handler already lives at `root/app/static/09_bootstrap.js:48-57`,
  warning when either editor's `state.dirty` is set — covering refresh / close /
  direct-nav / typed-URL **and** D2's full-reload Back/Forward. So phase 10a
  needs **no new dirty-guard work**. The in-app `popstate` confirm **shipped in
  phase 10c** (wraps htmx's `window.onpopstate`; confirm + re-push on cancel +
  clear-dirty on confirm — see Phasing 10c).

## Design (per component)

### Server — `root/app/server/`
- Add a small helper `shell_or_fragment(active_tab)` (in `_shared.py`) used by
  the five item views. Pseudo:
  ```
  def wants_shell(req):
      # D1: shell only for a genuine browser navigation. HTMX swaps carry
      # HX-Request; programmatic/test clients carry neither -> both get the
      # fragment, preserving the /ui/* fragment contract. Back/Forward is a
      # full reload (D2), itself a navigation, so it lands here too.
      if req.headers.get("HX-Request"):
          return False
      return req.headers.get("Sec-Fetch-Mode") == "navigate"
  ```
  When `wants_shell`, the view returns
  `render_shell(initial_main_url=request.full_path, active_tab=...)` and
  **short-circuits** (no need to render the fragment server-side — the client
  re-fetches it via the `#main-pane` load trigger). Otherwise it renders the
  fragment exactly as today.
- `render_shell(...)` renders `base.html` with `tree`, `run_results`,
  `initial_main_url`, `active_tab`, `active_path` — the same context `index()`
  passes today, plus the three new keys. `index()` becomes
  `render_shell("/ui/folder/", "tree", active_path="")`.
- A 404 from an item view (HX path) still returns the 404 fragment into the
  pane; a non-HX GET to a bad item returns the shell, then the in-pane fetch
  surfaces the 404. (Acceptable; noted.)

### Shell — `root/app/templates/base.html`
- `#main-pane`: `hx-get="{{ initial_main_url|default('/ui/folder/') }}"`.
- `#sidebar` carries `data-active-tab="{{ active_tab|default('tree') }}"`.
- New globals near the existing `window.TMS_RUN_RESULTS`:
  `window.TMS_ACTIVE_TAB`, `window.TMS_ACTIVE_PATH`.
- Active-tab button classes may stay defaulted to `tree`; bootstrap calls
  `tmsSwitchSidebarTab(window.TMS_ACTIVE_TAB)` which fixes classes + lazy-mounts
  the non-tree pane when needed.

### Client — `root/app/static/`
- `09_bootstrap.js`: set `htmx.config.historyCacheSize = 0`; on boot, if
  `TMS_ACTIVE_TAB !== "tree"` call `tmsSwitchSidebarTab(TMS_ACTIVE_TAB)`; seed
  `tmsExpandedFolders` with the active item's ancestors (D6) before the tree's
  restore; register the `beforeunload` + `popstate` dirty guards (D7).
- `01_tree.js`: no logic change; it already restores from `tmsExpandedFolders`.
- Nav templates get `hx-push-url="true"` (D5): `tree.html` (folder name span +
  file/other rows), `test_run_sidebar.html` (group rows + run leaves),
  `reports_sidebar.html`, `enums_sidebar.html`, the folder views
  (`folder_module.html`, `folder_subfolder.html`, `folder_project.html`,
  `folder_test_run_area.html`, `folder_test_run_group.html`), breadcrumbs, and
  report/run row links.

## Step plan

1. **Server negotiation** → verify: non-HX GET `/ui/file/<p>` returns
   `base.html` (doctype + `#main-pane` `hx-get` = that path + `active_tab=tree`);
   HX GET returns the fragment; `HX-History-Restore-Request` returns the shell.
2. **`base.html` parameterization** + `index()` via `render_shell` → verify:
   `/` unchanged (root folder, tree tab); active-tab derivation per route.
3. **`hx-push-url` on nav elements** → verify: the enumerated nav elements carry
   `hx-push-url="true"`; sidebar refresh / lazy-mount / SSE elements do **not**.
4. **Bootstrap** (history cache off, tab restore, tree-expand seed, dirty
   guards) → verify via static-wiring smokes + a render smoke for active-path.
5. **Regression** → full smoke suite green; manual: open a run, refresh, hit
   Back/Forward across folder→file→run, confirm editors boot and the tree opens
   to the item.

## Test plan (`.smoke-scratch/tech-10/`)

- `T10_01` server negotiation: shell vs fragment vs history-restore (headers).
- `T10_02` active-tab derivation for all five item routes.
- `T10_03` `index()` + `base.html`: default `initial_main_url` / tab; the new
  globals are emitted.
- `T10_04` template wiring: nav elements carry `hx-push-url`; sidebar/SSE/lazy
  elements do not.
- `T10_05` bootstrap static: `historyCacheSize = 0`, tab restore call, ancestor
  seeding, `beforeunload` dirty guard (no `popstate` confirm in v1).
- `T10_06` end-to-end-ish: non-HX `/ui/run/<p>/<g>/<f>` → shell with
  `active_tab=test-run` + `active_path` set; HX → run-editor fragment.

## Resolved (was: open questions)

- **OQ1 → resolved: reuse `/ui/...`** as the visible URL (D3). No separate
  public-URL map layer; `hx-push-url="true"` is a literal (push URL == request
  URL), keeping the template edits trivial.
- **OQ2 → resolved: `beforeunload` only** for v1 (D7). The in-app `popstate`
  dirty-confirm is a deferred follow-up.

## Deferred follow-ups (post-v1)

- In-app Back/Forward (`popstate`) dirty-confirm with re-push on cancel.
- A cleaner public URL scheme (e.g. `/app/<type>/<path>`) mapped onto the
  fragment renderers, if the `/ui/...` address bar reads too "internal".

## Pre-implementation spike (recommended)

The one cross-cutting **assumption** is HTMX 2.x history behavior in this app:
that with `htmx.config.historyCacheSize = 0` a Back/Forward issues a server GET
carrying `HX-History-Restore-Request`, that returning the full `<body>`
replaces the history element AND re-runs its `<script>` tags (so `tmsBootShell`
+ editor boots fire) AND re-fires `#main-pane`'s `hx-trigger="load"`. Verify
with a ~30-min throwaway spike wiring one route (`/ui/run/...`) end-to-end
(refresh + Back/Forward). If the script-rerun assumption fails, the fix is
small (an `htmx:historyRestore` hook) but it would amend D2.
