# Feature 11 — Test-case project-level enums — coverage matrix (Step 1 audit)

Spec source: `specs/features/11-feature-testcase-component-NEW.md`
(731 lines). v1 ships `components` as the first enum kind; the model /
parser / serializer / validator / editor all generalise over any kind
defined in a project's `enums.yaml`.

Source files in scope:
- `app/models.py` — `Feature.enums` field, `ENUM_IDENTIFIER_RE`,
  `validate_feature` enum rules, `to_dict`/`from_dict`.
- `app/gherkin_io.py` — `parse_feature` pre-parse `# enum.<kind>: <key>`
  scan, `serialize_feature` directive emit.
- `app/storage.py` — `read_project_enums`, `init_project_enums`,
  `create_folder` depth-1 auto-init, `write_feature` enum cross-check,
  mtime cache, `list_tree` `enums.yaml` filter, `_ENUMS_FILE_NAME`.
- `app/errors.py` — `EnumsParseError`.
- `app/server.py` — `GET`/`POST /api/enums/<project>`,
  `EnumsParseError` handler, the `PATCH /api/files` / `PUT .../raw`
  cross-check side-effect.
- `app/templates/file_editor.html` — `#feature-enums` section scaffold.
- `app/static/app.js` — `tmsEditor` enums wiring (`_vocabCache`,
  `_loadEnums`, `renderEnums`, `_initEnumsFile`).

## Method

Same conventions as features 01–10:
- One stable ID per spec rule; one smoke per rule (or tight cluster).
- HTTP / storage round-trips end-to-end via the Flask test client.
- Pure-JS editor wiring covered by **static regex inspection** of
  `app/static/app.js` (no JS runtime) — already the approach taken by
  the existing `F11_09` smoke.

Rule-ID groups: `M*` model, `PR*` parser, `SR*` serializer, `RE*`
read_project_enums, `IN*` init, `CF*` create_folder auto-init, `WF*`
write_feature cross-check, `VS*` visibility/reservation, `EH*` error
handler, `HT*` HTTP routes, `ED*` editor, `AC*` acceptance criteria.

## Existing-smoke inventory (root-level — Step 2 candidates)

9 `s11_*/s12_*/s13_*` smokes at the `.smoke-scratch/` root primary-frame
feature-11 (they test the enums model / storage / HTTP+editor slices
S1/S2/S3 directly). All 9 pass today but are **not** discovered by
`run.py` (it only walks `feature-*/F<N>_*`).

| Smoke | Slice | Asserts |
|---|---|---|
| `s11_a_feature_enums_field.py` | S1 | `Feature.enums` field, to/from_dict, `ENUM_IDENTIFIER_RE`, validate rules |
| `s11_b_parser_enum_directives.py` | S1 | parse extracts directives; cutoff; non-directive comments ignored; malformed kind/key/empty-key raise |
| `s11_c_serialize_and_roundtrip.py` | S1 | serializer alphabetical emit, empty skipped, legacy byte-identical, round-trip, whitespace canonicalisation |
| `s12_a_enums_parse_error_envelope.py` | S2 | `EnumsParseError` → 422 `enums_parse_error` `{line,column}` |
| `s12_b_read_project_enums.py` | S2 | all `read_project_enums` branches + schema rejections + mtime cache |
| `s12_c_storage_lifecycle.py` | S2 | `init_project_enums`, `create_folder` auto-init, `list_tree` filter, write_feature cross-check matrix, missing-file rule |
| `s13_a_enums_routes.py` | S3 | GET/POST `/api/enums/<project>` all status branches |
| `s13_b_editor_scaffold.py` | S3 | `#feature-enums` scaffold + 4 sub-elements + Init button + payload |
| `s13_c_editor_controller_wires.py` | S3 | `tmsEditor` enums wiring (cache, loadEnums, renderEnums, picker change, orphans, init POST) |

## Matrix

Status: `covered` / `partial` / `missing` / `n/a`.

### Model — `Feature.enums` (M)

| # | Rule | Smoke | Status |
|---|---|---|---|
| M1 | `Feature.enums: dict[str,str]` default `{}`; `to_dict`/`from_dict` carry it. | `F11_01` | covered |
| M2 | `validate_feature`: every kind name matches `^[A-Za-z_][A-Za-z0-9_]*$`. | `F11_01` | covered |
| M3 | values are empty-string OR single-line identifier-regex strings. | `F11_01` | covered |
| M4 | empty value always legal (unset); pure model never rejects unknown kind/key. | `F11_01` | covered |

### Parser — `# enum.<kind>: <key>` (PR)

| # | Rule | Smoke | Status |
|---|---|---|---|
| PR1 | leading directives populate `Feature.enums`. | `F11_02` | covered |
| PR2 | non-directive comments ignored; co-exists with `# language:`. | `F11_02` | covered |
| PR3 | comments at/after the first tag / `Feature:` cutoff are NOT extracted. | `F11_02` | covered |
| PR4 | duplicate `kind` in the header → `GherkinParseError`. | `F11_10` | covered |
| PR5 | malformed kind / malformed key / empty key → `GherkinParseError` at parse. | `F11_02` | covered |
| PR6 | leading whitespace tolerated; trimmed before regex match. | `F11_03` (canonicalisation) | covered |
| PR7 | docstring-internal `# enum.…` lines (past cutoff) are NOT extracted. | `F11_11` | covered |

### Serializer (SR)

| # | Rule | Smoke | Status |
|---|---|---|---|
| SR1 | one `# enum.<kind>: <key>` per non-empty entry, alphabetical, above tags/`Feature:`. | `F11_03` | covered |
| SR2 | empty-string values skipped. | `F11_03` | covered |
| SR3 | empty `enums` dict → no directives; legacy files byte-identical. | `F11_03` | covered |
| SR4 | round-trip stable + canonicalises whitespace + alphabetical order. | `F11_03` | covered |

### Storage — `read_project_enums` (RE)

| # | Rule | Smoke | Status |
|---|---|---|---|
| RE1 | missing file → `FileNotFoundError`. | `F11_05` | covered |
| RE2 | default `components:\n` → `{"components": {}}`. | `F11_05` | covered |
| RE3 | empty / comment-only / `None` root → `{}`. | `F11_05` | covered |
| RE4 | well-formed multi-kind parses + preserves insertion order. | `F11_05` | covered |
| RE5 | malformed YAML → `EnumsParseError(line)`. | `F11_05` | covered |
| RE6 | non-mapping root → `EnumsParseError`. | `F11_05` | covered |
| RE7 | schema rejects non-list kind / non-dict elem / multi-key elem / bad-id key / multi-line label / dup inner key. | `F11_05` | covered |
| RE8 | mtime cache: hit returns same object; miss re-reads after mtime bump. | `F11_05` | covered |

### Storage — init / auto-init / cross-check / visibility (IN/CF/WF/VS)

| # | Rule | Smoke | Status |
|---|---|---|---|
| IN1 | `init_project_enums` writes exact `components:\n` bytes; refuses overwrite (`NameConflictError`); refreshes cache. | `F11_06` | covered |
| CF1 | `create_folder` depth-1 (project create) writes both folder + default `enums.yaml`; deeper folders do not. | `F11_06` | covered |
| WF1 | `write_feature` with known `(kind, key)` passes. | `F11_06` | covered |
| WF2 | unknown kind → `ValidationError(enums[<kind>])`. | `F11_06` | covered |
| WF3 | unknown key for a known kind → `ValidationError(enums[<kind>])`. | `F11_06` | covered |
| WF4 | all-empty enums skip the cross-check (no YAML read). | `F11_06` | covered |
| WF5 | label rename in `enums.yaml` doesn't break an existing key save. | `F11_06` | covered |
| WF6 | missing-file rule: non-empty enums → 422; empty passes. | `F11_06` | covered |
| VS1 | `list_tree` hides `enums.yaml` at depth 2 (project root). | `F11_06` | covered |
| VS2 | `list_folder` at depth 1 returns only modules (no file-filter needed). | — (no-op per spec) | n/a |
| VS3 | `_validate_segment` / `_reject_reserved_typed_area` forbid a depth-2 folder named `enums.yaml`. | `F11_12` (drift pinned) | covered |

### Error handler + HTTP routes (EH/HT)

| # | Rule | Smoke | Status |
|---|---|---|---|
| EH1 | `EnumsParseError` → 422 `enums_parse_error` `{line,column}` envelope. | `F11_04` | covered |
| HT1 | `GET /api/enums/<p>` legacy (no file) → 404 `not_found`. | `F11_07` | covered |
| HT2 | `GET` auto-initialised → 200 `{components:{}}`. | `F11_07` | covered |
| HT3 | `GET` hand-written multi-kind → 200 parsed dict (order preserved). | `F11_07` | covered |
| HT4 | `GET` malformed YAML → 422 `enums_parse_error` w/ line. | `F11_07` | covered |
| HT5 | `POST` legacy → 201, default bytes, body carries the enums dict. | `F11_07` | covered |
| HT6 | `POST` already-init → 409 `name_conflict` (no overwrite). | `F11_07` | covered |
| HT7 | `POST` missing project folder → 404. | `F11_07` | covered |
| HT8 | `POST`→`GET` round-trip returns identical body. | `F11_07` | covered |
| HT9 | `PATCH /api/files/<p>` / `PUT .../raw` cross-check → 422 `validation_error` (field `enums[<kind>]`) on bad enum; file unchanged. | `F11_13` | covered |

### Editor (ED — static JS + render-and-grep)

| # | Rule | Smoke | Status |
|---|---|---|---|
| ED1 | `#feature-enums` wrapper + missing/empty/pickers/orphans sub-elements. | `F11_08` | covered |
| ED2 | `Initialize enums file` button present; missing-state hidden initially. | `F11_08` | covered |
| ED3 | no regression on legacy structured-tab ids. | `F11_08` | covered |
| ED4 | `editor-data` payload carries `feature.enums`. | `F11_08` | covered |
| ED5 | session `_vocabCache` keyed by project. | `F11_09` | covered |
| ED6 | `_loadEnums` fetches `GET /api/enums/<project>` (URL-encoded). | `F11_09` | covered |
| ED7 | `renderEnums` wired into `renderStructured()` reload path. | `F11_09` | covered |
| ED8 | `<select>` change → `state.feature.enums[kind]` + `markDirty(true)`. | `F11_09` | covered |
| ED9 | orphan rows rendered per the join logic (`kind∉vocab` or `key∉vocab[kind]`). | `F11_09` | covered |
| ED10 | `tmsEditor.boot()` wires Init button + kicks off `_loadEnums`; `_initEnumsFile` POSTs, hydrates cache, transitions to `ok`. | `F11_09` | covered |
| ED11 | empty-list kind renders a disabled control with the "edit `enums.yaml`" hint. | `F11_14` | covered |
| ED12 | options render `<option value="<key>">{label}` with a leading `— not set —` empty option. | `F11_15` | covered |
| ED13 | raw tab shows `# enum.<kind>: <key>` verbatim (keys only). | SR1/SR4 (`F11_03`) | n/a |

### Acceptance criteria (AC — dedupe)

All AC rows dedupe onto the rules above (project-create auto-init →
CF1/IN1; POST 201/409 → HT5/HT6; GET 422 → HT4; round-trip key-only →
SR1/SR4; non-directive comments untouched → PR2; unknown key/kind 422 →
WF2/WF3; label rename no-op → WF5; legacy byte-identical → SR3;
adaptability / new kind → covered by the generic model; orphan handling
→ WF + ED9). Tracked there; `n/a` here.

## Tally (Step 4 complete)

- Every countable rule across M/PR/SR/RE/IN/CF/WF/VS/EH/HT/ED is now
  `covered`; `missing` = 0.
- `n/a`: VS2 (no-op per spec), ED13 (raw verbatim = SR1/SR4), and the
  AC dedupe rows.
- Smoke files: **15** (`F11_01..F11_15`) — 9 moved in Step 2 + 6
  gap-fillers in Step 4.

## Drift — confirmed + pinned (VS3)

The spec said `_validate_segment` / `_reject_reserved_typed_area` were
"extended to also forbid a depth-2 folder named `enums.yaml`". As
shipped there is **no** such segment-level reservation: `enums.yaml`
is guarded only *incidentally* by the auto-init file occupying that
name. On a project whose enums file is absent, a folder literally
named `enums.yaml` is creatable. `F11_12` asserts the real behaviour
and pins the drift (no code change; flags the spec wording for a
future reconciliation pass).

## Open sign-off questions (Step 1)

1. **Step-2 move set.** Move all **9** `s11_*/s12_*/s13_*` root smokes
   into `feature-11/`, renamed `F11_01..F11_09` and re-sequenced by
   slice (S1 model/parser/serializer → S2 storage → S3 HTTP/editor).
   No cross-credit stays at root (all 9 primary-frame feature-11).
   Approve?
2. **Static JS inspection** for the `tmsEditor` enums wiring (no
   runtime) — continue the existing `F11_09` approach. Approve?
3. **Step-4 gap-fill targets.** New smokes for PR4 (duplicate-kind →
   GherkinParseError), PR7 (docstring-internal directive ignored), VS3
   (depth-2 `enums.yaml` folder rejection — verify/pin drift), HT9
   (cross-check 422 via `PATCH /api/files` + `PUT .../raw`), ED11
   (empty-list disabled picker + hint) and ED12 (`— not set —` option +
   `value="<key>"`/label split). Approve this gap list?
4. **Split granularity.** Same heuristic (~90 LOC, split on distinct
   setup / failure modes). The existing 9 are cohesive per slice; new
   gap-fill smokes will be small and single-purpose. Approve?

## Step 1 — sign-off (Jun 9, 2026)

All four decisions **approved**: (1) move all 9 root smokes into
`feature-11/` as `F11_01..F11_09`; (2) static JS inspection for the
editor wiring; (3) the Step-4 gap list (PR4, PR7, VS3, HT9, ED11,
ED12); (4) the standard split granularity.

## Step 2 — executed (9 smokes moved + renamed)

`.smoke-scratch/` is gitignored, so plain `mv` was used. Files were
re-sequenced by slice (S1 → S2 → S3) and verified in 3 batches, each
run file-by-file; all 9 pass individually. None use `__file__`/
`parents` (cwd-relative or test-client only), so the deeper location
did not break path resolution.

| Old (root) | New (`feature-11/`) | Slice |
|---|---|---|
| `s11_a_feature_enums_field.py` | `F11_01_model_enums_field.py` | S1 |
| `s11_b_parser_enum_directives.py` | `F11_02_parser_directives.py` | S1 |
| `s11_c_serialize_and_roundtrip.py` | `F11_03_serialize_roundtrip.py` | S1 |
| `s12_a_enums_parse_error_envelope.py` | `F11_04_enums_parse_error.py` | S2 |
| `s12_b_read_project_enums.py` | `F11_05_read_project_enums.py` | S2 |
| `s12_c_storage_lifecycle.py` | `F11_06_storage_lifecycle.py` | S2 |
| `s13_a_enums_routes.py` | `F11_07_enums_routes.py` | S3 |
| `s13_b_editor_scaffold.py` | `F11_08_editor_scaffold.py` | S3 |
| `s13_c_editor_controller_wires.py` | `F11_09_editor_controller.py` | S3 |

No smokes stayed at root (all 9 primary-frame feature-11).

**Suite results after the move:**
- `python .smoke-scratch/run.py --filter feature-11` → **9/9** pass.
- `python .smoke-scratch/run.py` (full) → **206/206** pass (was 197;
  the 9 moved smokes are now discovered by the runner).

Next: Step 3 (refine moved smokes — check for stale `s1x` cross-refs),
then Step 4 (gap-fill PR4/PR7/VS3/HT9/ED11/ED12).

## Step 3 — executed (cross-reference refines)

The 9 moved smokes needed **no internal refines** — a grep for
`s11`/`s12`/`s13` inside `feature-11/F11_*.py` returns nothing (they
are self-contained, use cwd-relative / test-client paths, and never
cite each other by filename).

The real Step-3 work was fixing **stale cross-references in other
features' docs/smokes** that pointed at the old root paths:

- `feature-01/COVERAGE.md` — P9 note + I1 cross-credit + the Step-1
  "closest neighbours" note: `s11_b`/`s11_c` → `F11_02`/`F11_03`
  (full paths `feature-11/F11_0{2,3}_*.py`).
- `feature-08/COVERAGE.md` — TP4/TP6 matrix cross-credits and the
  Step-2 candidate notes: `s13_b`/`s13_c` → `F11_08`/`F11_09`; the
  now-false "Stays in root" lines corrected to "Moved … in
  feature-11 Step 2".
- `feature-08/F08_05_structured_tab.py` — docstring cross-credit
  `s13_b_editor_scaffold.py` → `feature-11/F11_08_editor_scaffold.py`.

The only remaining `s1x` mentions are intentional historical records:
this file's inventory table + the Step-2 rename map, and the
feature-08 "Moved from root `s13_b`/`s13_c`" provenance notes.

**Suite after refines:** `--filter feature-11` → 9/9; full → 206/206.

## Step 4 — executed (6 smokes written, all passing)

6 gap-fill smokes written (`F11_10`–`F11_15`), each verified
individually then as a suite:

- `F11_10_parser_duplicate_kind.py` — PR4 (duplicate kind → GherkinParseError).
- `F11_11_parser_cutoff_docstring.py` — PR7 (directives past the cutoff / inside a docstring not extracted).
- `F11_12_enums_yaml_folder.py` — VS3 (drift pinned — see above).
- `F11_13_file_route_crosscheck.py` — HT9 (cross-check 422 via PATCH /api/files + PUT .../raw; file unchanged).
- `F11_14_picker_empty_disabled.py` — ED11 (empty-list kind → disabled control + hint).
- `F11_15_picker_options_notset.py` — ED12 (`— not set —` empty option; options submit key / display label; stored key pre-selected).

Notes from execution:

- PR4 and PR7 were already implemented in `app/gherkin_io.py`
  (`_extract_enum_directives`: duplicate-kind guard + `line >= cutoff`
  skip) — the smokes confirm them end-to-end.
- VS3 is a confirmed documentation drift (no code change) — pinned by
  `F11_12`.

- As a suite: `python .smoke-scratch/run.py --filter feature-11` →
  **15/15 passed; 0 failed**.
- Full repo suite: `python .smoke-scratch/run.py` →
  **212/212 passed; 0 failed**.

Coverage: **all countable rules covered; 0 missing.** Feature-11
test-case enums is fully covered.

## Condition-coverage gap-closer (Jun 9, 2026)

`F11_16_enums_yaml_dir_listed.py` closes condition-coverage gap
"Pattern C": the project-enums hide in `Storage._tree_children`
(`if depth == 1 and name == _ENUMS_FILE_NAME and entry.is_file()`) had
its `is_file() == True` leg covered by VS1 (`F11_06`), but the
`is_file() == False` leg — a **directory** named `enums.yaml` at depth 1
(a module inside a project) — was never exercised. This creates such a
directory (after deleting the auto-init file, cf. `F11_12`) and asserts
it is **listed** as a folder, while a sibling project's real
`enums.yaml` FILE stays hidden. No new spec rule — hardens VS1's
condition coverage. (feature-11 now 16 smokes.)
