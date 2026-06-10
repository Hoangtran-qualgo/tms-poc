# 06 · Tree pane

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/templates/tree.html`, `app/templates/base.html` (wiring),_
_`app/server/routes_tree.py` (`ui_tree`), `app/static/01_tree.js`_
_(`toggleTreeFolder`, `tmsExpandedFolders`, `tmsRestoreTreeState`)._

## Summary

Left-sidebar navigation widget that renders the data root as a
nested folder/file tree. Initial paint is server-side included into
`base.html`; subsequent refreshes happen automatically via SSE
(`sse:change` → swap) and manually via a refresh button rendered
inside the partial itself.

As of Phase 2 of `10-feature-test-run` (Jun 5, 2026), the tree pane
is one of two tabs in a vertical-tab sidebar (the other being the
*Test run* tab; see `10-feature-test-run-NEW.md`). The shell-level
restructure — tab strip, drag-to-resize, collapse — lives in
`app/templates/base.html` and `app/static/02_sidebar.js`'s
`tmsSwitchSidebarTab` / `tmsInitSidebar` block; this spec's scope
remains the inner tree partial itself.

## Scope

In scope:

- Recursive rendering of `Storage.list_tree()` output as nested
  `<ul>` rows, one row per folder or file.
- Click handlers: folder name → load the corresponding folder
  view; file row → load the file editor (or unsupported view).
- Caret toggle for expand/collapse with state preserved across
  re-renders.
- SSE-driven auto-refresh on every `"change"` event.
- Manual refresh button (`↻`) at the top of the partial.
- Empty-state placeholder when the data root has no projects.

Out of scope:

- Folder / file CRUD entry points (live in their own features —
  the tree only navigates, never mutates).
- The main-pane content itself (`07-folder-views`, `08-file-editor`).
- Per-event SSE payloads — the pane always refetches the full
  tree, never a delta.

## Public surface

Template:

- `app/templates/tree.html` — `render_children(children)` macro
  emits one `<li>` per child. Folders have a caret button and a
  name span (separate so the caret toggles without navigating).
  Files emit `<div class="tree-file">` with an `hx-get` to
  `/ui/file/<path>`; non-feature files emit
  `<div class="tree-other">` with the same hx-get (the route maps
  them to `unsupported.html`).

Route:

- `GET /ui/tree` → renders `tree.html` with
  `tree = storage.list_tree()`. Used for the manual refresh button
  and the SSE auto-refresh.

Wiring (`app/templates/base.html`):

- `<body hx-ext="sse" sse-connect="/api/events">` — SSE subscription
  for the whole page.
- `<aside id="tree-pane" hx-get="/ui/tree" hx-trigger="sse:change"
  hx-swap="innerHTML">` — the partial is swapped wholesale on every
  bus message. The element is one of two sibling panels inside
  `#sidebar-panels`; the other (`#test-run-pane`) is hidden by
  default and lazy-mounted on its first tab activation.

Client state (`app/static/01_tree.js`):

- `const tmsExpandedFolders = new Set()` — folder paths the user
  has expanded. Module-scope; survives tree re-renders.
- `toggleTreeFolder(rowEl)` — manual toggle invoked by the caret's
  inline `onclick`. Updates DOM and the Set.
- `tmsRestoreTreeState()` — re-applies the Set to a freshly-
  rendered tree. Hooked into `htmx:afterSwap` for `#tree-pane`.

## Invariants & rules

**`test-run/` is hidden from the directory tree**

`Storage.list_tree()` filters out any child literally named
`"test-run"` of a depth-1 (project) folder. Other depths are
untouched — a folder named `test-run` at depth 3 (e.g.
`WebStore/Checkout/test-run/`) is still listed, because the typed
area is depth-2 only (see `02-storage-core` `RESERVED_DEPTH2_NAMES`).

Symmetrically, `Storage.list_folder(parts)` filters `"test-run"`
out of the returned `modules` list when `len(parts) == 1`, so
`folder_project.html`'s module table hides the typed area too.

Test runs are reached exclusively via the *Test run* sidebar tab
(`10-feature-test-run`).

**Server-side initial render**

`base.html` does `{% include "tree.html" %}` so the first paint is
fully populated; HTMX is *not* on the critical path for first
render. The `hx-get="/ui/tree"` on the `#tree-pane` aside fires
only on subsequent `sse:change` events.

**SSE-driven refresh**

- Any FS change inside the data root, surviving the watcher's
  filters (`02-storage-core`'s temp regex + self-write
  suppression), publishes one `"change"` event after the debounce
  window.
- Every connected tab swaps `/ui/tree` into `#tree-pane` and
  invokes `tmsRestoreTreeState()` to re-expand previously open
  folders.
- The writing tab does *not* receive the event (`_mark_write`
  covers it); its tree is updated by other code paths
  (`tmsRefreshFolder` after a CRUD operation, or the editor's own
  re-route).

**Manual refresh button**

- Rendered inside `tree.html` itself, so every swap re-renders the
  button (stateless).
- Pure HTMX: `hx-get="/ui/tree" hx-target="#tree-pane"
  hx-swap="innerHTML"`. No JS.
- `aria-label="Refresh tree"` + `title` for accessibility.

**Click navigation**

- Caret button: `event.stopPropagation()` + `toggleTreeFolder(...)`.
  Does NOT trigger HTMX.
- Folder name span: `hx-get="/ui/folder/<path>"` →
  `#main-pane`. Works at any depth. Sub-folders under modules
  navigate to their own view via `folder_subfolder.html`.
- File rows: `hx-get="/ui/file/<path>"` → `#main-pane`. Non-
  `.feature` rows use the same hx-get; the route returns
  `unsupported.html`.

**Expanded-state preservation**

- Toggling the caret mutates `tmsExpandedFolders`.
- `htmx:afterSwap` on `#tree-pane` runs `tmsRestoreTreeState()`,
  which walks `[data-path]` rows and re-expands any path in the
  Set. Folders that disappeared between renders simply drop off
  (path no longer in DOM).
- Tabs see their own state; the Set is per-page, not synchronised
  across tabs.

## Affects

- `02-storage-core`: consumes `Storage.list_tree()` output verbatim;
  any future schema change there propagates here.
- `03-watcher-and-sse`: this is the *only HTMX-wired* subscriber
  of the `"change"` event (via `hx-trigger="sse:change"` on
  `#tree-pane`). The file editor (`08-file-editor`) also reacts to
  the same event but through a vanilla
  `document.body.addEventListener("sse:change", ...)` listener,
  not through HTMX. Every other feature relies on the tree-refresh
  side-effect (e.g. `04-folder-crud` doesn't refresh itself; the
  tree does).
- `07-folder-views` and `08-file-editor`: every link in the tree
  invokes their respective UI routes via HTMX.

## Depends on

- `02-storage-core` for `Storage.list_tree()`.
- `03-watcher-and-sse` for the `sse:change` trigger.
- HTMX 2.x with `htmx-ext-sse@2` (declared in `base.html`).
- `app/static/01_tree.js` for `toggleTreeFolder` /
  `tmsRestoreTreeState`.
- Tailwind CDN (visual; no behavioural dependency).

## Surface for follow-up

- Per-event SSE payloads would let the tree re-render only the
  affected sub-tree instead of the whole pane. Today it's a full
  refetch; cheap for current workloads, would scale poorly to
  large repos.
- A future "select highlight" (show which file is currently open
  in the editor) would need editor-side cooperation to broadcast
  the current path; not wired in v1.
- Drag-and-drop reordering / drag-to-move are not implemented;
  `05-testcase-crud` exposes the `move` API that such a feature
  would call.
- Tree filtering / search-as-you-type at the sidebar level is not
  implemented; users go through the top-bar search (`09-search`)
  instead.

## Acceptance criteria

- The first paint of the page shows the tree fully populated
  without any HTMX request having fired.
- Out-of-band edits (terminal `touch`, external IDE saves) cause
  exactly one `/ui/tree` swap per debounced burst on every open
  tab.
- Expanding a folder, then triggering an external change, leaves
  that folder still expanded after the refresh.
- Clicking the `↻` refresh button issues exactly one `GET /ui/tree`
  and re-applies the expanded state.
- Clicking a folder name navigates the main pane; clicking the
  caret does not.
- Clicking a `.feature` file row loads the file editor; clicking
  a non-feature file row loads `unsupported.html`.
