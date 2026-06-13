# 06 · Quality-report detail — extra columns

_Status: **Shipped Jun 13, 2026** (decisions RP-1 / RP-2 `key : label` /
RP-3 name-always-present). Enhancement to `feature-12`. See the as-built
summary at the foot of this file and `DONE.md`._

## Scope

The report aggregation engine `app/reporting.py` and the detail template
`app/templates/report_detail.html`. Four asks:

1. **Case trend:** add a `run name` column. Today the table is `Run | When
   | Result`, where the **Run** cell shows the run *file name* (`t.run`)
   and links via `run_path`; add the human `run.name` as a new column →
   `Run | Run name | When | Result`.
2. **Tag ranking:** per-case detail gains `scenario name` + `enums`.
3. **Enum ranking:** per-case detail gains `scenario name` + `tags`.
4. **Tag inventory:** per-case detail gains `scenario name` + `enums`.

Out of scope: charts (feature-12 lock-in), the ranking aggregation logic
itself, and any change to report config/storage.

## Depends on

- **tech-04 migration** (scenario name populated), else the new
  scenario-name cells are blank for legacy cases.

## Current state (grounded)

- Reports render **tables + collapsible lists only** (feature-12 "Out of
  scope" — no charts).
- **Ranking / inventory** buckets each carry a per-case list
  `cases: [{file_path, …}]` (`reporting.py:208,227,306`), rendered as
  **folder-grouped, filename-only** links inside a `<details>` disclosure
  (`report_detail.html:96-135`). The bucket summary row is `label | bar |
  count | %` (`:85-95`) — it has **no** per-case column, so the new
  fields attach to the **per-case list**, not the ranking row.
- **Case trend** rows are `{run: <file_name>, run_path, created_at,
  result}` (`reporting.py:257-264`); the loaded `run` object already
  exposes `run.name`. Template table is `Run | When | Result`
  (`report_detail.html:165-186`).
- The `.feature` for each case is already read into a per-call cache in
  every engine function (`_read_feature(storage, cache, path)`), so
  `scenario.name` / `enums` / tags are available with **no extra I/O**.

## Proposed approach

### A. Case trend — add run name (ask 1)

- `_case_trend`: add `"run_name": run.name` to each trend dict
  (`reporting.py:257-264`).
- Template: insert a **Run name** column. Columns become `Run | Run name |
  When | Result` (the existing "Run" cell is the run path/file link, kept
  as-is). Empty `run.name` → fall back per RP-3.

### B. Ranking / inventory — enrich per-case entries (asks 2–4)

- When appending to `cases` (and the `carrying` list for inventory),
  also include, from the already-cached `Feature`:
  - `enum_ranking` cases → `scenario_name`, `tags`.
  - `tag_ranking` cases → `scenario_name`, `enums`.
  - `tag_inventory` carrying cases → `scenario_name`, `enums`.
  - synthetic / `(removed)` cases (feature is `None`) →
    `scenario_name=""`, empty `enums`/`tags`.
- Template: turn each per-case `<li>` (`report_detail.html:120-123`) into
  a compact row showing filename + scenario name + the extra dimension
  (enums or tags). Keep the folder grouping + click-through `hx-get`.

## Decisions (resolved Jun 13, 2026)

- **RP-1 — Ranking "column" = per-case enrichment.** Confirmed: ranking
  rows are buckets (label/count/%), so the new fields live in the
  expandable per-case list, not the bucket row.
- **RP-2 — Enums display → `key : label`.** Threaded `project` + a
  best-effort vocab read (`_read_vocab`) into `_tag_ranking` /
  `_tag_inventory`; each enum renders `key : label`. Since `write_feature`
  cross-checks every stored enum (kind + key) against `enums.yaml`, stored
  values always resolve in normal operation — the **only** blank-label
  path is a missing / unreadable `enums.yaml` at report time, which
  degrades silently to key-only (no warning, enums are secondary here).
- **RP-3 — `run.name` is always present.** Re-investigated: `POST /runs`
  requires a non-empty `name`, `validate_run` enforces non-empty +
  single-line, and every write goes through `_serialize_run` →
  `validate_run`. So the case-trend column renders `run.name` directly —
  no `—` / file-name fallback is needed.

## Assumptions / blindspots

- **RP-4.** Enrichment is free — the `Feature` is already cached per
  compute; no added reads.
- **RP-5 (test impact).** `F12_22_detail_per_type.py` asserts each type's
  distinctive render markers (ranking buckets; case_trend timeline table) —
  re-pin it for the new columns. The S1 aggregation smokes that assert the
  per-bucket `cases[]` entry shape and the `trend[]` dict shape gain fields
  (additive — existing keys stay).
- **RP-6.** `tag_ranking` is multi-valued (a case appears under every tag
  it carries); the same case row (with its scenario name + enums) repeats
  across buckets — expected, matches D10.
- **RP-7.** Live recompute on `sse:change` (D5) still holds; extra fields
  are pure render data.

## As-built (shipped Jun 13, 2026)

- **DO-1 — case trend** (`reporting.py` + `report_detail.html`).
  `_case_trend` adds `"run_name": run.name` per trend row; the timeline
  table gains a **Run name** column → `Run | Run name | When | Result`
  (the **Run** cell stays the run-file link).
- **DO-2 — engine enrichment** (`reporting.py`). New helpers `_read_vocab`
  (tolerant project-enum read → `{}`) and `_case_enums` (`{kind, key,
  label}` sorted by kind; label blank when it is missing or equals the
  key). `compute_report` now passes `project` to `_tag_ranking` /
  `_tag_inventory`. Per-case entries gain: `enum_ranking` →
  `scenario_name` + `tags`; `tag_ranking` + `tag_inventory` →
  `scenario_name` + `enums`. Tombstoned / `(removed)` cases enrich to
  blanks (`scenario_name=""`, empty list).
- **DO-2 — template** (`report_detail.html`). Each per-case `<li>` shows
  the **scenario name** (prominent) `·` **case path** (muted mono link)
  plus the type's extra dimension — `@tags` (enum-ranking) or `key : label`
  enums (tag-ranking / inventory).
- **UI follow-ups (same day, on USER request):**
  - Per-case row: scenario name made the prominent identity
    (`text-slate-800 font-medium`), the case path de-emphasised to a muted
    mono link, separated by a `·` divider — clearer contrast / separation.
  - Bucket bar contrast: track = total (dark grey `bg-slate-400`); fill =
    dark green (`bg-green-600`) for real "valid" buckets, orange
    (`bg-orange-500`) for synthetic "invalid" ones (unset/removed/untagged).
- **CHECK.** New `tech-06/T06_01..03` (+`COVERAGE.md`); re-pinned
  `F12_22` was unaffected, but `F12_02` was re-pinned for the additive
  per-case keys (RP-5). Full suite **282/282 PASS** (was 279).
- **ACT.** `DONE.md` entry added; backlog item cleared from
  `IN-PROGRESS.md`; this spec marked shipped.
</CodeContent>
<parameter name="EmptyFile">false
