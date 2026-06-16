# tech-08 · Test-case list revamp (Enums column + top-3 Tags) — coverage matrix

Smoke coverage against
`specs/tech/08-tech-testcase-list-revamp-NEW.md` (shipped Jun 15, 2026).

## Method

- Spec source: `specs/tech/08-tech-testcase-list-revamp-NEW.md` (decisions
  LR-1 storage-local helper · LR-2 `key : label` · LR-3 cap = **3** + `n
  more…` with full set in `title` · LR-4 5-column widths · LR-5 em-dash empty
  · LR-6 best-effort parse failure).
- `T08_01` pins the storage row shape; `T08_02` pins the rendered table.
- `Status`: `covered` (data-shape assertion), `render` (HTML marker assertion).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| DO-1: `list_folder` rows carry `enums: [{kind, key, label}]` | `tech-08/T08_01_list_row_enums` | covered |
| LR-2: selected enum resolves its `enums.yaml` label (`p1` → `Priority 1`) | `tech-08/T08_01_list_row_enums` | covered |
| Redundant `label == key` collapses to `label == ""` (template shows key alone) | `tech-08/T08_01_list_row_enums` | covered |
| Unset enum (empty-string value) is skipped | `tech-08/T08_01_list_row_enums` | covered |
| Rows are kind-sorted | `tech-08/T08_01_list_row_enums` | covered |
| LR-6: parse-failure file still lists with `enums == []` (and `tags == []`) | `tech-08/T08_01_list_row_enums` | covered |
| DO-2 / LR-3: Tags column shows first 3 chips + `+N more…`; full union in `title` | `tech-08/T08_02_list_render_top3` | render |
| DO-2 / LR-2+LR-3: Enums column shows first 3 `key : label` chips + `+N more…`; full list in `title` | `tech-08/T08_02_list_render_top3` | render |
| LR-5: empty Tags / Enums cell renders an em-dash | `tech-08/T08_02_list_render_top3` | render |
| Existing union-of-feature+scenario tags rendering (3-tag fixture, under cap) | `feature-07/F07_04c_tags_column` (unchanged) | render |

## Notes

- **Decisions (Jun 15, 2026):** LR-2 → `key : label` (reuse tech-06's
  report-detail format). Cap raised from the spec's proposed 2 → **3** per
  USER request, for both Tags and Enums. LR-1 → a storage-local
  `_enum_display_rows` helper (not an import from the `reporting` engine
  layer), keeping `list_folder` self-contained.
- **No re-pin of `feature-07/F07_04c`.** It seeds exactly 3 tags
  (`@regression @smoke @critical`); at a cap of 3 all chips still render with
  no overflow, so the existing union assertion holds. The >3 overflow path is
  covered by `T08_02` (4 tags / 4 enums → 3 chips + `+1 more…`).
- **`missing enums.yaml → key-only` is intentionally not fixtured.** Like
  tech-06, a stored enum is impossible to construct without a readable vocab
  (`write_feature` cross-checks every key against `enums.yaml`), so the
  best-effort `vocab = {}` branch in `list_folder` is defensive only.
- **Depends on tech-04** (scenario name is the identity; the middle column
  already shows it) and **tech-06** (`key : label` enum display precedent).
- Full suite at sign-off: **289/289 PASS / 0 FAIL** (was 287; +2 tech-08).
