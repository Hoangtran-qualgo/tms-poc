# tech-07 · Require `scenario_name` at the create API — coverage matrix

Smoke coverage against
`specs/tech/07-tech-require-scenario-name-create-api-NEW.md` (shipped
Jun 15, 2026).

## Method

- Spec source: `specs/tech/07-tech-require-scenario-name-create-api-NEW.md`
  (decisions SN-1=A API-only · SN-2=standard 400 `bad_request` · SN-3=strip-aware).
- One new tech-07 smoke pins the `POST /api/files` contract directly;
  `F05_07_create_body` is the canonical create-body contract (rewritten from
  the old "scenario_name optional → 201" rule).
- `Status`: `covered` (status-code / on-disk assertion), `re-pin` (existing
  smoke updated to the new contract).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| SN-1: `POST /api/files` with `scenario_name` omitted → 400 `bad_request` | `tech-07/T07_01_require_scenario_name` | covered |
| SN-1: empty `scenario_name` (`""`) → 400 `bad_request` | `tech-07/T07_01_require_scenario_name` | covered |
| SN-3: whitespace-only `scenario_name` (`"   "`) → 400 (stripped == empty) | `tech-07/T07_01_require_scenario_name` | covered |
| SN-2 / type guard: non-string `scenario_name` → 400 `bad_request` | `tech-07/T07_01_require_scenario_name` | covered |
| Happy path: valid `scenario_name` → 201 + `scenario.name` on disk | `tech-07/T07_01_require_scenario_name` | covered |
| Regression: description stays OPTIONAL (tech-04 D1) under the new gate | `tech-07/T07_01_require_scenario_name` | covered |
| Canonical create-body contract (file_name + scenario_name required; description optional; non-string rejected; identity echoed) | `feature-05/F05_07_create_body` (rewritten) | re-pin |
| Ordering: scenario_name guard does not mask the original guard | `feature-05/F05_12` (type), `feature-10/F10_51` (reserved area), `feature-10/F10_52` (yaml ext) | re-pin |

## Notes

- **Decision (Jun 15, 2026): Option A (API-only).** Enforcement added in
  `post_file` only (`app/server/routes_files.py`), reusing
  `_require_non_empty_string` + a strip-aware check (SN-3). The model (V5),
  `create_file`, `validate_feature`, PATCH/PUT-raw, and the editor save-gate
  are intentionally left permissive — this mirrors how the shipped **import**
  feature (`feature-14` / `import_feature_cases`) enforces scenario names at
  the use-case entry point, not in the model, and preserves tech-04 D1's
  bare-`Scenario:` round-trip.
- **Residual (accepted):** `storage.create_file(...)` can still be called
  programmatically with an empty name. That is an internal primitive (no HTTP
  surface), the same trust boundary as import — not a product hole.
- **Blast radius (as built > estimate).** The spec estimated "≈ 3 files"; the
  real Option-A radius was **38 smoke files / 64 `POST /api/files` create
  sites** (a too-narrow grep had missed multi-line POST bodies). The fix was
  still mechanical (add a valid `scenario_name`) except `F05_07` (full
  contract rewrite). No `storage.create_file` fixtures were touched — Option B
  would have re-pinned ~400 such sites.
- Full suite at sign-off: **287/287 PASS / 0 FAIL** (was 286; +1 tech-07).
