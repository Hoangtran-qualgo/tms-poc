# 07 · Require `scenario_name` at the create API

_Status: **SHIPPED Jun 15, 2026** (Option A — API-only entry-point
enforcement; SN-1=A, SN-2=standard 400, SN-3=strip-aware all signed off)._
_Deferred from `tech-04` (Option B); filed as a Must-have in `IN-PROGRESS.md`._

## As built (Jun 15, 2026)

- **DO-1 — API.** `post_file` now requires a non-empty `scenario_name` via
  `_require_non_empty_string` + a strip-aware guard (SN-3); the stale
  tech-04 "Option B / deferred" comment is gone
  (`@/Users/hoang.tv/Documents/Projects/tms/app/server/routes_files.py:43-54`).
  Model (V5), `create_file`, `validate_feature`, PATCH/PUT-raw, and the
  editor save-gate are unchanged — enforcement lives at the one HTTP entry
  point, mirroring `import_feature_cases`.
- **DO-1 CHECK.** New `tech-07/T07_01_require_scenario_name` — missing /
  empty / whitespace-only / non-string → 400 `bad_request`; valid → 201 with
  `scenario.name` on disk; description still optional (tech-04 D1).
- **DO-2 — re-pin.** The Option-A blast radius was larger than the original
  "≈ 3 files" estimate (a too-narrow grep missed multi-line POST bodies):
  **38 smoke files / 64 `POST /api/files` create sites** across
  `feature-04/05/06/07/08` + `tech-03`. `F05_07_create_body` was a full
  contract rewrite (was "scenario_name optional → 201"); `F05_12`, `F10_51`,
  `F10_52` were ordering-sensitive (kept their original guard the
  discriminator). No `storage.create_file` fixtures were touched.
- **Full suite: 287/287 PASS** (286 prior + new `T07_01`). See
  `tech-07/COVERAGE.md`.

## Scope

Close the one remaining gap where a `.feature` file can be created with an
**empty scenario name** through the HTTP API, even though the create modal
requires it client-side (tech-04 RG1).

Decide **where** to enforce "scenario name required" on the write path —
and, by extension, whether the permissive model rule (V5) should become
strict.

## Current state (grounded Jun 15, 2026)

- **API permissive.** `POST /api/files` reads `scenario_name` with a default
  of `""` and only type-checks it; an empty value is accepted and passed to
  `create_file` (`@/Users/hoang.tv/Documents/Projects/tms/app/server/routes_files.py:44-69`).
- **Storage permissive.** `create_file(parts, description="", *,
  scenario_name="")` writes a placeholder `Scenario(kind="scenario",
  name=scenario_name)` — empty is allowed and serialises to a bare
  `Scenario:` line that round-trips
  (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_features.py:40-81`).
- **Model permissive (V5 / Option B).** `validate_feature` checks
  `scenario.name` is **single-line** but **not non-empty**
  (`@/Users/hoang.tv/Documents/Projects/tms/app/models/_feature.py:360-364`).
  This is deliberate (tech-04 D1: an empty description + empty scenario name
  round-trips as bare `Feature:` / `Scenario:` lines).
- **UI already strict.** The create modal `tmsCreateFile` gates Save on a
  non-empty scenario name client-side (tech-04 RG1); the editor Save-gate
  likewise keys on `scenario.name`.
- **Import already strict (use-case layer).** `import_feature_cases` adds a
  pre-flight reason `"scenario #N: scenario name is required."` and writes
  nothing when any scenario name is empty
  (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_features.py:202-203`).
  Note: import enforces this **in the use-case method, not in the model** —
  so the established pattern is *entry-point* enforcement with a permissive
  model.

> **Correction to the backlog note:** the import feature does **not** enforce
> scenario name "client-side only" — it already enforces server-side in
> `import_feature_cases`. The only unguarded server entry point is
> `POST /api/files`.

## Options

### Option A — API-only (entry-point enforcement) — _recommended_

- Require a non-empty `scenario_name` in `post_file` (reuse
  `_require_non_empty_string`, returning the existing 400 `bad_request`
  shape). Leave `create_file`, `validate_feature`, and the editor save
  paths unchanged.
- **Consistency:** mirrors exactly how `import_feature_cases` already
  enforces it (entry-point, not model). Keeps the tech-04 D1 round-trip and
  the placeholder-`create_file` primitive intact.
- **Blast radius:** only the few HTTP `POST /api/files` smokes that create a
  *valid* file without `scenario_name` (≈ `F10_51`, `F05_07`/`F05_01`
  create-body, and any setup helper that POSTs files). Direct
  `storage.create_file(...)` fixtures (the bulk, ~60+ files) are **not**
  affected.
- **Residual:** `storage.create_file` can still be called with an empty name
  programmatically — acceptable, because storage primitives are internal and
  the only HTTP surface is now guarded (same trust boundary as import).

### Option B — Model-level V-rule (strict everywhere)

- Add a non-empty `scenario.name` invariant to `validate_feature`, making
  every serialised feature require a name: `create_file`,
  `create_feature_file`, `write_feature` (PATCH), `write_raw` (PUT raw), and
  the editor all reject empty.
- **Consistency:** strongest — one rule, enforced uniformly; the backlog's
  "stricter API + matching model V-rule" reading.
- **Blast radius (large):** ~412 `create_file` / `write_feature` call sites
  across ~60+ smoke files build placeholder fixtures with empty scenario
  names; all would need a name added. Must also re-verify
  `scripts/backfill_scenario_names.py` and any round-trip smoke that relies
  on a bare `Scenario:` line. **Reverses tech-04 D1** for scenario name.
- **Risk:** high churn, easy to miss a fixture, and it re-pins many smokes
  whose subject is unrelated (depth rules, locking, search, etc.).

## Recommendation

**Option A.** It closes the actual hole (the one unguarded HTTP entry
point), matches the import feature's existing enforcement layer, and avoids
re-pinning dozens of unrelated setup smokes or reversing the tech-04 D1
round-trip decision. Option B's uniformity is not worth its churn given the
model is intentionally permissive for placeholder + round-trip support.

## Decisions (to resolve before DO)

- **SN-1 — Enforcement layer: A (API-only) vs B (model V-rule)?**
  _Proposed: **A**._
- **SN-2 — Error shape.** API-only returns the standard 400 `bad_request`
  (`_require_non_empty_string`'s message). _Proposed: yes, no new error
  code._
- **SN-3 — Whitespace-only names.** Treat `"   "` as empty (strip before the
  non-empty check), matching `import_feature_cases`' `.strip()` rule.
  _Proposed: yes._

## Proposed approach (Option A, pending sign-off)

1. **DO-1 — API.** In `post_file`, replace the permissive
   `scenario_name = body.get("scenario_name", "")` block with
   `_require_non_empty_string(body.get("scenario_name"), "scenario_name")`
   (strip-aware per SN-3); drop the now-stale "Option B / deferred" comment.
   **CHECK:** new `tech-07/T07_01` — `POST /api/files` without / with empty /
   with whitespace `scenario_name` → 400 `bad_request`; with a real name →
   201 + file on disk with that scenario name.
2. **DO-2 — re-pin affected smokes.** Add a `scenario_name` to the few HTTP
   `POST /api/files` create calls that currently omit it (identified at DO
   time by running the suite). Do **not** touch `storage.create_file`
   fixtures. **CHECK:** full suite green.
3. **ACT.** `DONE.md` entry, `tech-07/COVERAGE.md`, clear the `IN-PROGRESS.md`
   Must-have, mark this spec shipped.

## Out of scope

- Changing the model's V5 permissiveness (that is Option B; explicitly not
  chosen unless SN-1 flips).
- Requiring a non-empty **feature description** (tech-04 D1 keeps it
  optional).
- Any change to the editor save-gate (already strict client-side).
