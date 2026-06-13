# tech-06 · Quality-report detail extra columns — coverage matrix

Smoke coverage against
`specs/tech/06-tech-report-detail-columns-NEW.md` (shipped Jun 13, 2026).

## Method

- Spec source: `specs/tech/06-tech-report-detail-columns-NEW.md`
  (asks 1–4; decisions RP-1 / RP-2 `key : label` / RP-3 name-always-present).
- New tech-06 smokes pin the engine view-model shapes + the detail render
  markers; `F12_02` re-pinned for the additive per-case keys (RP-5).
- `Status`: `covered`, `render` (HTML marker assertion).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| Ask 1: `_case_trend` attaches the human `run.name` per trend row (alongside the file name `t.run`) | `tech-06/T06_01_case_trend_run_name` | covered |
| Ask 1: detail render adds a `Run name` header column showing `run.name` | `tech-06/T06_01_case_trend_run_name` | render |
| RP-3: runs always have a non-empty name (write-time enforced) → column renders `run.name` directly, no fallback | `tech-06/T06_01_case_trend_run_name` | covered |
| Ask 2: `tag_ranking` per-case entries carry `scenario_name` + `enums` (`{kind,key,label}`, sorted by kind) | `tech-06/T06_02_ranking_enum_enrichment` | covered |
| RP-2: enum label is the human `enums.yaml` value → rendered `key : label` | `tech-06/T06_02_ranking_enum_enrichment` | covered + render |
| Ask 4: `tag_inventory` carrying per-case entries get the same `scenario_name` + `enums` enrichment | `tech-06/T06_02_ranking_enum_enrichment` | covered |
| RP-2 tolerant degrade: missing/unreadable `enums.yaml` at report time → blank label (key only), no crash | `tech-06/T06_02_ranking_enum_enrichment` | covered |
| Ask 3: `enum_ranking` per-case entries carry `scenario_name` + sorted `tags` (not enums) | `tech-06/T06_03_enum_ranking_tags_and_removed` | covered |
| RP-4: tombstoned `(removed)` case enriches to blanks (`scenario_name=""`, empty list) | `tech-06/T06_03_enum_ranking_tags_and_removed` | covered |
| Ask 3: detail render shows the scenario name + the case's tags | `tech-06/T06_03_enum_ranking_tags_and_removed` | render |
| RP-5 (additive impact): per-bucket `cases[]` entries gain `scenario_name`/`enums` without dropping `file_path` | `feature-12/F12_02_tag_ranking_multivalue` (re-pinned) | covered |

## Notes

- **Decisions (Jun 13, 2026):** RP-1 confirmed (per-case enrichment, not a
  bucket-row column). RP-2 → `key : label` (threaded `project` + a tolerant
  `_read_vocab` into `_tag_ranking` / `_tag_inventory`). RP-3 → run name is
  guaranteed non-empty at write time, so no `—` / file-name fallback.
- **Blank-label reality:** because `write_feature` cross-checks every stored
  enum (kind + key) against `enums.yaml`, stored values always resolve in
  normal operation — the only blank-label path is a missing / unreadable
  vocab at report time, covered by T06_02's degrade case. An "unknown enum
  key" fixture is *impossible* to construct via `write_feature` (rejected
  with a `ValidationError`).
- **Same-day UI follow-ups (USER request), not separately smoked (pure CSS
  / layout):**
  - Per-case row: scenario name prominent (`text-slate-800 font-medium`),
    case path muted mono link, `·` divider — contrast / separation.
  - Bucket bar: track grey `bg-slate-400` (total), fill `bg-green-600`
    (valid / real) vs `bg-orange-500` (invalid / synthetic).
  The render smokes still pass because they assert content strings
  (scenario name, `key : label`, `@tag`) that survive the restyle.
- **Depends on tech-04 migration** (already run) so scenario-name cells are
  populated for legacy cases.
- Full suite at sign-off: **282/282 PASS / 0 FAIL** (was 279; +3 tech-06).
