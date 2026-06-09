# 09 · Search

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/storage.py` (`Storage.search`), `app/server.py`_
_(`/api/search`, `/ui/search`), `app/templates/search_results.html`,_
_`app/templates/base.html` (top-bar form), `app/static/app.js`_
_(`tmsWireSearch`)._

## Summary

Top-bar global search over `.feature` files. Two match modes
(`text` against `Feature.description`, `tag` against
`Scenario.tags`) and three scopes (`all`, `project:<name>`,
`module:<project>/<module>`). Empty / 1-hit / many-hit result
states are distinct UX paths: empty → message, one hit → auto-
navigate, many → list. Input fires on Enter or after a 300 ms
typing pause; the wiring is plain JS rather than HTMX trigger
filters because of an HTMX 2.x quirk documented in DONE.md.

## Scope

In scope:

- The top-bar form (`#search-form` in `base.html`) — query input,
  scope select, match-mode select, case-sensitive checkbox.
- `tmsWireSearch` debounce + Enter + on-change re-fire logic.
- The `/api/search` JSON endpoint and the `/ui/search` HTML
  endpoint (the latter renders `search_results.html`).
- `Storage.search` substring matching with hit-shape contract.
- The three-variant result template: empty state, 0 hits, 1 hit
  (auto-navigate), ≥ 2 hits (list view).

Out of scope:

- Editing test cases from search results (clicking a row opens
  the file editor — see `08-file-editor`).
- Folder browsing (`07-folder-views`).
- Full-text search of step text, examples tags, or feature tags
  (none searched in v1).

## Public surface

Routes:

- `GET /api/search` — query string `q`, `scope`, `match`, `case`.
  Returns `{ hits: [SearchHit, ...] }`.
- `GET /ui/search` — same query string. Renders
  `search_results.html`. Empty `q` returns the partial with
  `show_empty_state=True` and `hits=[]`.

Storage method:

- `Storage.search(query, *, scope="all", match="text",
  case_sensitive=False) -> list[dict]`.
- `match="text"`: substring against `Feature.description`; at
  most one hit per file.
- `match="tag"`: substring against each value in
  `Scenario.tags`; one hit per matching tag (so a file with
  multiple matching tags emits multiple hits, each carrying the
  matched tag value).
- `scope`: `"all"` | `"project:<name>"` | `"module:<proj>/<mod>"`.
- `case_sensitive`: defaults `False`. Case-insensitive matching
  is implemented via `str.lower()` on both needle and haystack
  (not `str.casefold()`); minor Unicode-folding edge cases (e.g.,
  German ß) therefore round-trip as-is.

Hit shape:

```
{
  "file_path": "<project>/<module>/<…>/<name>.feature",
  "description": "<Feature.description>",
  "matched_field": "description" | "tag",
  "match_value": "<the query (text mode) | the matched tag (tag mode)>"
}
```

UI form (`base.html`):

- `#search-q` (text input), `#search-scope` (select),
  `#search-match` (select), `#search-case` (checkbox), inside
  `<form id="search-form" onsubmit="event.preventDefault();">`.
- Wired explicitly in JS rather than via HTMX trigger filters
  because `keyup[key=='Enter']`-style filters silently fail under
  HTMX 2.x (see DONE.md "Search function does not display
  results").

`tmsWireSearch` (`app/static/app.js`):

- `q.keydown` Enter → cancel debounce, fire immediately.
- `q.input` → schedule fire after 300 ms.
- `scope` / `match` / `case` `change` → fire immediately *iff*
  `q.value.trim()` is non-empty.
- `fire()` calls `htmx.ajax("GET", "/ui/search?...", { target:
  "#main-pane", swap: "innerHTML" })`.

## Invariants & rules

**Match semantics**

- Substring match (no regex, no fuzzy).
- Default case-insensitive via `str.lower()` on both sides.
- Empty / whitespace-only `query` returns `[]` at the storage
  layer; the UI layer also short-circuits to the empty-state
  partial when `q` is blank.
- Files that fail to parse (`GherkinParseError`, `OSError`,
  `UnicodeDecodeError`) are silently skipped during the walk.
  The user must repair them via the tree / file editor.
- `match="text"`: matches anywhere in `Feature.description`
  (real-newline string, NOT the on-disk literal `\n`).
- `match="tag"`: substring against each tag value (already
  stripped of `@`). One hit per matching tag.

**Scope filter**

- `"all"`: every file under the data root.
- `"project:<name>"`: only files whose first segment is `<name>`.
- `"module:<proj>/<mod>"`: only files whose first two segments
  match.
- Invalid scope syntax → `ValueError` (HTTP 400 / inline 400
  snippet via UI handler).

**Result UX (`search_results.html`)**

- `show_empty_state=True` (empty query case): "Type a query in
  the search box above and press Enter."
- `len(hits) == 0`: "No matches for <q>" + hint.
- `len(hits) == 1`: inline `<script>` runs `htmx.ajax("GET",
  "/ui/file/<file_path>", { target: "#main-pane", … })` —
  auto-navigates to the file editor.
- `len(hits) >= 2`: table with file_path / first-line description
  / match badge. Each row is an `hx-get` to `/ui/file/<path>`.

**Input firing**

- Empty queries never fire from the input. The server still
  accepts them (returns the empty-state variant); the client
  skips to avoid stale-flash of empty-state HTML between
  keystrokes.
- Enter cancels any pending debounce and fires immediately.
- 300 ms is the only debounce; not configurable.

**Tag input convention**

- Users type tag values without the `@` in the input. The match
  is against the bare values stored in the model, not the
  rendered `@`-prefixed chips.

## Affects

- `02-storage-core`: `Storage.search` is the entire backend.
- `07-folder-views`: the main pane swaps to search results, then
  back to folder views via row clicks.
- `08-file-editor`: every search result row's hx-get opens the
  editor.
- `06-tree-pane`: not directly affected — the tree stays in
  place during search; only `#main-pane` swaps.

## Depends on

- `02-storage-core` for `Storage.search` and the data-root walk.
- `01-gherkin-io` for the parsed `Feature` objects whose
  `description` and `scenario.tags` are searched.
- `app/static/app.js` (`tmsWireSearch`) for the debounce / Enter
  / on-change logic; HTMX `htmx.ajax(...)` for the actual swap.
- Tailwind CDN for layout (visual only).

## Surface for follow-up

- **Step text, feature tags, and examples tags are NOT searched**
  in v1. A future expansion would add `match` values (e.g.
  `match=step`, `match=any`) and corresponding `matched_field`
  values in the hit shape.
- **No regex / boolean / phrase operators**. Substring only.
- **Result ordering** today reflects on-disk walk order; no
  ranking by match quality or freshness.
- The pending `test-report` Investigate item plans to compute
  tag-presence percentages over filtered sets of test cases —
  reuses `Storage.search` with `match="tag"` plus a per-folder
  scope, then aggregates.
- The pending folder-level test-case filter Investigate item
  (`IN-PROGRESS.md`) likely extends `Storage.search` (or adds a
  sibling endpoint) with contain / not-contain rules over tag
  groups; current substring-only model would need an upgrade.

## Acceptance criteria

- An empty query renders the "Type a query…" empty state and
  fires no `GET /api/search`.
- A query that matches exactly one file auto-navigates the main
  pane to that file's editor without an intermediate list view.
- A `match=text` query that appears inside a Feature.description
  emits exactly one hit for that file.
- A `match=tag` query that appears inside two distinct tag
  values on the same scenario emits two hits for that file (one
  per matching tag).
- Changing `scope` / `match` / `case` while the query is non-
  empty re-fires search immediately.
- Typing fast then pausing fires exactly one search after the
  300 ms pause (not one per keystroke).
- Pressing Enter cancels the pending debounce and fires
  immediately.
