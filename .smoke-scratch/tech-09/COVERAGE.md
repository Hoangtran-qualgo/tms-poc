# tech-09 · Scenario Outline in test runs — coverage matrix

Smoke coverage against
`specs/tech/09-tech-outline-import-run-NEW.md` (**Shipped Jun 16, 2026**).
All of DO-1..DO-6 covered; full suite **301/301 PASS**.

## Method

- Spec source: `specs/tech/09-tech-outline-import-run-NEW.md`
  (decisions D1–D7 + DQ1; DO-1..DO-6).
- New tech-09 smokes pin each DO step 1:1 (`T09_01`..`T09_06`).
- `Status`: `covered`, `static` (JS / template invariant by source
  inspection), `pending` (DO step not yet built).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| DO-1 / D1: `split_example_suffix` parses ` -- @<table>.<row>` (1-based ints), whitespace-tolerant; plain names → `(stripped, None)` | `tech-09/T09_01_split_example_suffix` | covered |
| DO-1 / D4: an outline's report rows trim to ONE shared base, with distinct `{table,row}` (no false collapse) | `tech-09/T09_01_split_example_suffix` | covered |
| DO-1: names that merely contain `--` or a non-anchored token are returned whole (no mis-split) | `tech-09/T09_01_split_example_suffix` | covered |
| DO-2 / D2: `RunResult.example` + uniqueness key `(file_path, example)`; legacy plain `to_dict` shape unchanged; YAML round-trip + malformed coercion | `tech-09/T09_02_runresult_example` | covered |
| DO-3 / D4: import keeps an outline's rows distinct (not ambiguous/collapsed); counts tally ROWS not distinct bases; each row carries its `example` | `tech-09/T09_03_import_outline_rows` | covered |
| DO-3: commit writes same-path results with distinct examples + plain row; unmatched suffixed row errors on FULL name + aborts all-or-nothing | `tech-09/T09_03_import_outline_rows` | covered |
| DO-4 / D3+D7: run-editor display — outline result shows base name + live Examples header + matched data row (keyed by `data-example`); out-of-range table/row degrades to base-only (tolerant blank) | `tech-09/T09_04_editor_display` | covered |
| DO-4 / DQ1: removed case → "file has been removed" note under the filename (Test-case column); remark-column override dropped; scenario cell blank | `tech-09/T09_04_editor_display` | covered |
| DO-5 / A4: "+ Add test case" expands a Scenario Outline into one row per Examples data row (1-based {table,row}); plain/unreadable case -> one row | `tech-09/T09_05_manual_add_roundtrip` | covered |
| DO-5 / BS-F: example stamped on `data-example`, carried by `_readCurrent`, keyed by `_compareJson`/`_sortKey`; survives the PATCH wire in order; duplicate (file_path,example) -> 422 | `tech-09/T09_05_manual_add_roundtrip` | covered |
| DO-6: end-to-end on the real bundled Allure sample (9 scenarios incl. `count -- @1.1`/`@1.2`) — preview 9/9 matched + per-row counts, commit writes 2 same-path example results + 7 plain, editor renders the Examples rows | `tech-09/T09_06_sample_end_to_end` | covered |

## Notes

- **DO-1 grounded against the real sample** (`specs/sample-data/allure-report-single/`):
  the two outline rows are `'…count -- @1.1 '` / `'…count -- @1.2 '` (trailing
  space), both trimming to base `'Verify retrieve agent conversations count'`.
- **Base is fully stripped** (not just rstripped): leading/trailing whitespace
  on a base name is never meaningful and the resolver matches scenario names
  exactly (case-folded), so stripping both ends is the safe, consistent choice.
- Helper lives in `app/allure_io.py` (`split_example_suffix`), applied at the
  resolver/route boundary in DO-3 — `parse_allure_report` still reports raw
  leaf names so retry-collapse is unchanged.
- **DO-2 re-pin (better than planned):** `F10_43_validate_duplicate_filepath`
  needed **no** edit — it asserts only `"Duplicate" in message` + the
  `results[1].file_path` locator, both preserved. `F10_47` / `F10_56` plain-
  result shapes unchanged (example omitted when None). Full suite stayed green.
- **DO-3** shares one `_classify_report` helper across preview + commit
  (`routes_runs.py`): split suffix → resolve **distinct** base names → re-attach
  per row. Counts are tallied per ROW (`counts[row["match"]] += 1`), fixing the
  old `len(resolution[...])` collapse. Feature-14/15 import smokes stayed green.
- **DO-4** spans server + template + JS:
  - `routes_ui._resolve_example` resolves the live `(header, row)` for a pinned
    example; tolerant-blank (`None`) when not an outline / index out of range.
  - `run_editor.html`: row gains `data-example="<t>.<r>"`; scenario cell drops
    `truncate` and appends a `run-example` block; **DQ1** moves the removed-case
    cue to a `run-removed-note` under the filename and drops the remark override.
  - `06_run_editor.js._fillScenarioName` keeps its `(cell, file_path)` signature
    (T05_04 pins it) and reads the example from the row's `data-example`, mirroring
    the server resolve for async-added rows (exercised in DO-5/DO-6).
  - **Re-pin:** `F10_29` / `F10_75` updated old override text → `"file has been
    removed"`; `F10_33` (struck filename) + tech-05 cell smokes unaffected.
- **DO-5** is JS-only (`06_run_editor.js`); the PATCH route already round-trips
  `example` via `TestRun.from_dict` + `validate_run`, so no server change.
  - `_expandCasePaths` fetches each picked feature and emits one entry per
    Examples row for outlines (else a single null entry); the add-case
    `onConfirm` is now `async` and awaits it (modal already `await`s onConfirm).
  - `_createResultRow(file_path, example=null)` stamps `data-example`;
    `_readCurrent` adds `example` (omitted for plain); `_compareJson` rebuilds
    each result in canonical key order + sorts on `_sortKey` so DOM/Save/disk
    snapshots stringify identically (no false-dirty for same-path outline rows).
  - **Re-pin:** `F10_32` + `T05_04` regexes widened `_createResultRow(file_path`
    → tolerate the new optional `example` param (faithful, not weakened).
- **DO-6** drives the whole DO-1→DO-5 chain against the real bundled report
  (`specs/sample-data/allure-report-single/index.html`, 9 PASSED scenarios; the
  two `count -- @1.x` rows share base `Verify retrieve agent conversations
  count`). Seeds 8 cases (7 plain + 1 outline) so the import is all-matched,
  then asserts preview per-row counts, commit (2 same-path example results + 7
  plain, sample `created_at` preserved), and `/ui/run` rendering the Examples
  rows. No app code changed in DO-6 — pure end-to-end verification.
