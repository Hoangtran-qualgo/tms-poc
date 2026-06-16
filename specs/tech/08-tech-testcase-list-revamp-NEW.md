# 08 · Revamp the test-case list (Enums column + top-3 Tags)

_Status: **SHIPPED Jun 15, 2026.** Decisions: LR-2 = `key : label`;
**cap = top 3 + `n more…`** (raised from 2 per USER request) for both Tags
and Enums; LR-1 = storage-local helper; LR-3/4/5/6 as proposed._
_Filed as a Must-have in `IN-PROGRESS.md` ("Investigate: revamp test-case
list")._

## As built (Jun 15, 2026)

- **DO-1 — storage.** `Storage.list_folder` attaches `enums:
  [{kind, key, label}]` per feature row via a new storage-local
  `_enum_display_rows(enums, vocab)` helper (mirrors `reporting._case_enums`
  without importing the engine — LR-1)
  (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_listing.py:19-41`).
  The project vocab is read once per call (best-effort `{}` on
  missing/malformed `enums.yaml`); rows are kind-sorted, unset enums skipped,
  a redundant `label == key` blanked. Parse-failure files still list with
  `enums: []` (and `tags: []`) (`:256-302`).
- **DO-2 — template.** `_folder_feature_table.html` gains an **Enums** column
  (`key : label` chips, indigo, no `@`); **both** Tags and Enums cap to the
  first **3** chips + `+N more…`, with the full set in the cell `title`, and
  an em-dash when empty. Widths rebalanced to File `1/5` · Scenario `2/5` ·
  Tags `1/5` · Enums `1/5`.
- **DO-3 — tests.** New `tech-08/T08_01` (row shape) + `T08_02` (render:
  3 chips + `+1 more…` + full `title` + em-dash). `feature-07/F07_04c`
  needed **no re-pin**: at cap = 3 its 3-tag fixture still renders all chips
  (the overflow path is covered by `T08_02`).
- **Full suite: 289/289 PASS** (287 prior + 2 tech-08). See
  `tech-08/COVERAGE.md`.

## Scope

Two changes to the **folder-detail test-case list** (the shared features
table rendered at module depth 2 and sub-folder depths 3..MAX):

1. **New `Enums` column** — show the case's selected enums, **top 3 + `n
   more…`**.
2. **`Tags` column** — currently renders **every** chip; cap it to **top 3 +
   `n more…`** (same treatment as Enums).

This is a list-view-only revamp. It does **not** touch the editor, search,
the enum manager, or the model.

## Current state (grounded Jun 15, 2026)

- **Table markup** is shared in
  `@/Users/hoang.tv/Documents/Projects/tms/app/templates/_folder_feature_table.html:26-61`
  — 4 columns: a select checkbox (`w-10`), **File name** (`w-1/4`),
  **Scenario name** (`w-1/2`), **Tags** (`w-1/4`). It is `include`d by
  `folder_module.html` (depth 2) and `folder_subfolder.html` (depth 3+).
- **Tags cell renders ALL chips** today (no cap):
  `{% for t in f.tags %}<span …>@{{ t }}</span>{% endfor %}` inside a
  `truncate` `<td>`. Overflow is clipped by CSS, but every chip is emitted.
- **Row data** comes from `Storage.list_folder`
  (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_listing.py:246-266`):
  each row is `{file_name, description, scenario_name, tags}`. `tags` is the
  **order-preserving, de-duped union** of feature-level + scenario-level tags
  (D10; feature tags first). **No enums are attached to rows.** Parse
  failures still list the file with empty `description` / `scenario_name` /
  `tags`.
- **Enum data model.** `feature.enums` is a `dict[str, str]` of `kind → key`
  (`@/Users/hoang.tv/Documents/Projects/tms/app/models/_feature.py:167-179`).
  Enums are **feature-level**, which in the one-file = one-scenario model is
  the case identity, so "the scenario's enums" = `feature.enums`. An
  **empty-string value is the "unset" marker** and must be skipped. The only
  thing stored on disk is the key; human labels live in
  `<project>/enums.yaml` and are resolved at render time via
  `storage.read_project_enums(project)` → `{kind: {key: label}}`.
- **Reusable enum-display helper.** `reporting._case_enums(feature, vocab)`
  (`@/Users/hoang.tv/Documents/Projects/tms/app/reporting.py:156-175`) already
  produces `[{kind, key, label}, …]` **sorted by kind**, skipping unset keys,
  with `label=""` when it would be a redundant `key : key`. tech-06 renders
  these as **`key : label`**. _Caveat:_ this helper lives in the **engine**
  layer; `list_folder` lives in **storage** — see LR-1.
- **`top-2 + N more` precedent.** `fmtTags`
  (`@/Users/hoang.tv/Documents/Projects/tms/app/static/03_folder_actions.js:439-447`)
  formats a tag list as `@a @b +N more` (top 2, `@`-prefixed), em-dash when
  empty. This is client-side string formatting for the import-preview modal,
  not the server-rendered chip markup the list uses.
- **Smoke that pins the OLD behaviour.** `feature-07/F07_04c_tags_column`
  seeds a case with 3 tags (`@regression @smoke @critical`) and asserts **all
  three** chips render (`set(chips) >= {regression, smoke, critical}`). A
  top-2 cap makes this fail — it must be re-pinned (DO-3).

## Decisions (to resolve before DO)

- **LR-1 — Where to resolve enum labels for the list.** `list_folder`
  (storage) already attaches `scenario_name` + `tags` per row by parsing each
  feature, so attaching enums there is the consistent home. But the existing
  `_case_enums`/`_read_vocab` helpers live in `reporting` (engine), and
  storage must not import from the engine layer. _Proposed:_ attach enums in
  `list_folder`, reading the project vocab **once per call** via
  `self.read_project_enums(segments[0])` (best-effort: `{}` on missing /
  malformed), and factor the `{kind,key,label}` shaping into a small
  storage-local helper (mirroring `_case_enums`' rules). The engine helper
  stays as-is. _Alternative:_ extract `_case_enums` into a neutral module both
  layers import — more churn, deferred unless you prefer one source of truth.
- **LR-2 — Enum chip text. [RESOLVED: `key : label`.]** Reuse tech-06's
  **`key : label`** (label when present and non-redundant, else key alone),
  rendered as a chip visually distinct from tag chips (a different chip
  colour, **no `@` prefix**).
- **LR-3 — Which N, and what does `n more…` do? [N = 3 per USER request.]**
  **Tags** = first 3 of the union order (feature tags first, matching today's
  order); **Enums** = first 3 by `_case_enums`' kind-sorted order. The `+N
  more…` is **display-only text**; the **full set is placed in the cell's
  `title` attribute** so hover reveals everything (better than today's silent
  CSS clip).
- **LR-4 — 5-column layout / widths.** Adding Enums makes 5 columns.
  _Proposed:_ checkbox `w-10`, **File** `w-1/5`, **Scenario** `w-2/5`,
  **Tags** `w-1/5`, **Enums** `w-1/5`. Confirm the scenario column may shrink
  from `1/2` → `2/5`.
- **LR-5 — Empty cell.** _Proposed:_ render an em-dash `—` (muted) when a row
  has no tags / no enums, matching `fmtTags`. (Today the tags cell is simply
  blank.) Confirm, or keep blank.
- **LR-6 — Parse-failure rows.** Keep the existing best-effort contract:
  unparseable files list with empty enums (and empty tags), never crash the
  listing. _Proposed: yes._

## Proposed approach (pending sign-off)

1. **DO-1 — storage rows carry enums.** In `Storage.list_folder`, after
   parsing each feature, attach `enums: [{kind, key, label}, …]` (kind-sorted,
   unset skipped, redundant-label suppressed) using a vocab read once per
   call; empty list on parse failure or missing vocab. **CHECK:** new
   `tech-08` smoke pins the row shape (selected enum → `{kind,key,label}`;
   unset skipped; missing `enums.yaml` → key-only / empty label; parse failure
   → `[]`).
2. **DO-2 — render top-2 + `n more…`.** In `_folder_feature_table.html`: add
   the **Enums** `<th>`/`<td>` (chips, `key : label`), cap **both** Tags and
   Enums to the first 3 with a trailing `+N more…`, set the `title` to the
   full set, em-dash when empty, and rebalance widths (LR-4). **CHECK:**
   `tech-08` render smoke — exactly 3 chips + `+N more…` for a 4+ case; full
   list in `title`; em-dash when empty.
3. **DO-3 — re-pin.** Update `feature-07/F07_04c_tags_column` to the top-3
   contract (a 4-tag case shows 3 chips + `+1 more…` + full union in `title`,
   instead of all chips). Run the full suite. **CHECK:** suite green.
4. **ACT.** `DONE.md` entry, `tech-08/COVERAGE.md`, clear the `IN-PROGRESS.md`
   Must-have, mark this spec shipped.

## Out of scope

- The **Enums column ordering/format in search results** or the editor (this
  is the folder list only).
- Editing `enums.yaml`, or any change to `feature.enums` validation / the
  enum model.
- Folder-level **filtering** by tag/enum (separate Could-have item).
- Making `n more…` an interactive expander (tooltip-only here; revisit if
  users want click-to-expand).
