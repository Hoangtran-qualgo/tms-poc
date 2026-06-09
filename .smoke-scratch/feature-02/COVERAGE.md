# feature-02 · storage-core · coverage matrix

_Generated Jun 8, 2026 as Step 1 (Audit) of the smoke-suite
restructure plan in `IN-PROGRESS.md`._

## Method

- Spec source: `specs/features/02-feature-storage-core-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Bundled bullets split when sub-clauses are independently
  testable (e.g. `list_folder` returns one of four shapes by
  depth — split into DR3a/b/c/d).
- `Status` values: `covered`, `partial` (incidental coverage
  inside a primary-other-feature smoke), `missing`, `n/a`
  (rule is documentation-only / not testable). All rows in
  this matrix are testable; `n/a` count is **0**.
- `Smoke file` column carries the target file for every row.
  Per Decision A, feature-02 uses **one smoke per spec
  section** — eight files total
  (`F02_01_path_discipline.py` … `F02_08_acceptance.py`).
  All eight exist as of Step 4 (Jun 8, 2026).

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| PD1 | `_split(parts)` accepts either a list of segments or a `/`-joined string; rejects empty parts and `.` / `..` segments. | Invariants & rules → Path discipline | `F02_01_path_discipline.py` | covered |
| PD2 | `_validate_segment(seg)` rejects any segment containing `/ \ : * ? " < > |` or a control character (`0x00..0x1F`). | Path discipline | `F02_01_path_discipline.py` | covered |
| PD3 | `_resolve(parts)` returns an absolute `Path` strictly inside the data root; any escape raises `ValueError`. | Path discipline | `F02_01_path_discipline.py` | covered |
| PD4 | `.feature` extension auto-appended on create; create rejected if a different extension is supplied; comparison is case-insensitive (`MyTest.FEATURE` accepted). | Path discipline | `F02_01_path_discipline.py` | covered |
| DR1 | Folder creation requires `1 <= depth <= MAX_FOLDER_DEPTH` (10). | Depth rules | `F02_02_depth_rules.py` | covered |
| DR2 | `.feature` file location parent at `2 <= depth <= MAX_FOLDER_DEPTH`. Explicitly **not** enforced in `create_file` — storage trusts the segments it receives; enforcement lives at the API layer (feature-05 testcase-crud). The smoke for this row asserts the **trust** behaviour: `create_file` succeeds with a parent at depth 1 (below the API-layer minimum). | Depth rules | `F02_02_depth_rules.py` | covered |
| DR3a | `list_folder` at depth 0 returns `{kind: "root", …}`. | Depth rules | `F02_02_depth_rules.py` | covered |
| DR3b | `list_folder` at depth 1 returns `{kind: "project", …}`. | Depth rules | `F02_02_depth_rules.py` | covered |
| DR3c | `list_folder` at depth 2 returns `{kind: "module", folders, features}`. | Depth rules | `F02_02_depth_rules.py` | covered |
| DR3d | `list_folder` at depth 3..MAX returns `{kind: "subfolder", folders, features}`. | Depth rules | `F02_02_depth_rules.py` | covered |
| AW1 | Atomic write uses a temp name `<target>.tmp.<pid>.<uuid_hex>` in the same directory as the target. | Atomic write recipe | `F02_03_atomic_write.py` | covered |
| AW2 | Atomic write sequence: open → write → `fsync` → close → `os.replace` over the target. | Atomic write recipe | `F02_03_atomic_write.py` | covered |
| AW3 | On any failure during the atomic write, the temp file is unlinked and the original exception propagates. | Atomic write recipe | `F02_03_atomic_write.py` | covered |
| AW4 | Boot-time `cleanup_orphan_temp_files(root)` unlinks every file matching `TEMP_FILE_RE` and returns the count. | Atomic write recipe | `F02_03_atomic_write.py` | covered |
| NU1 | Name-uniqueness checks are scoped to the same parent only (siblings with the same name in different parents are allowed). | Name uniqueness | `F02_04_name_uniqueness.py` | covered |
| NU2 | Name-uniqueness is enforced via `target.exists()` — case-sensitivity follows the host filesystem; storage performs no explicit `casefold` / `lower` normalisation. | Name uniqueness | `F02_04_name_uniqueness.py` | covered |
| NU3 | File-extension matching IS explicitly case-insensitive via `name.lower()` — `MyTest.FEATURE` is accepted on any filesystem. (Overlaps PD4; kept separate for the case-insensitivity claim.) | Name uniqueness | `F02_04_name_uniqueness.py` | covered |
| NU4 | Name conflicts raise `NameConflictError(path, message)` (mapped to HTTP 409 by the API layer). | Name uniqueness | `F02_04_name_uniqueness.py` | covered |
| LK1 | `_lock_for(path_key)` returns a `_PathLock` (weakref-able wrapper around `threading.Lock`) kept in a `WeakValueDictionary`. | Locking | `F02_05_locking.py` | covered |
| LK2 | Single-target mutations acquire exactly one lock. | Locking | `F02_05_locking.py` | covered |
| LK3 | Dual-target mutations (rename / move / duplicate) acquire `sorted([src_key, dst_key])` — fixed ordering avoids deadlock. | Locking | `F02_05_locking.py` | covered |
| SW1 | After every successful mutation, `_mark_write(target)` records both `target` and `target.parent` (POSIX `DirModifiedEvent` bubbles up one level on mtime change). | Self-write bookkeeping | `F02_06_self_write.py` | covered |
| SW2 | Self-write entries expire `RECENT_WRITE_TTL_SECONDS` (500 ms) after they're written; opportunistic cleanup runs in the same lock window. | Self-write bookkeeping | `F02_06_self_write.py` | covered |
| SR1 | `search(query, match="text")` substring-matches `Feature.description`; at most one hit per file. | Search | `F02_07_search.py` | covered |
| SR2 | `search(query, match="tag")` substring-matches each tag in `Scenario.tags`; one hit per matching tag (multiple hits per file allowed). | Search | `F02_07_search.py` | covered |
| SR3 | `search` accepts `scope` ∈ `{all, project:<name>, module:<proj>/<mod>}` and filters results accordingly. | Search | `F02_07_search.py` | covered |
| SR4 | Each `SearchHit` has shape `{file_path, description, matched_field, match_value}`. | Search | `F02_07_search.py` | covered |
| AC1 | Reads, writes, and renames stay strictly inside the data root; any `..` or absolute segment raises `ValueError`. (Strengthens PD3 by stating it holds across read/write/rename.) | Acceptance criteria | `F02_08_acceptance.py` | covered |
| AC2 | Crash mid-write leaves the target byte-identical to the pre-write state; the temp file is recovered by the next boot scan. (Combines AW2 + AW4.) | Acceptance criteria | `F02_08_acceptance.py` | covered |
| AC3 | Concurrent saves of the same file via two threads are serialised; last-write-wins by lock release order. (Strengthens LK2 with a concurrency assertion.) | Acceptance criteria | `F02_08_acceptance.py` | covered |
| AC4 | Rename / move / duplicate never deadlock under any src/dst combination. (Strengthens LK3 with a stress-test assertion.) | Acceptance criteria | `F02_08_acceptance.py` | covered |
| AC5 | `_mark_write` plus `TEMP_FILE_RE` together suppress every watcher event generated by storage's own writes — no spurious SSE notification reaches the UI. (Strengthens SW1 + AW1 with the end-to-end suppression claim.) | Acceptance criteria | `F02_08_acceptance.py` | covered |

## Summary

- Total rules: **32** (4 path discipline, 6 depth rules, 4 atomic write, 4 name uniqueness, 3 locking, 2 self-write, 4 search, 5 acceptance, accounting for the splits noted under Method).
- `covered`: **32**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-02 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 02`
exits zero with all eight smokes green).

## Notes & flags

- **Zero direct coverage.** No existing smoke targets feature-02
  in its primary frame. The `p2_*` files in `.smoke-scratch/`
  are misleadingly named — `p2_` denotes the test-run
  feature's **Phase 2**, not feature-02. All `p2_*` and
  `p3_*` smokes are primary-feature-10 (`test-run`); the
  `s11_*` / `s12_*` / `s13_*` smokes are primary-feature-11
  (`testcase-component`). Three feature-10 smokes
  (`p2_2e`, plus the `p3_*` series for create-run-group)
  exercise `Storage.create_folder` / `Storage.create_run_group`
  but do not *assert* feature-02 rules — they assert
  end-to-end SSE / UI behaviour. No partial credit awarded.
- **Correction to `IN-PROGRESS.md`.** The
  "Feature-01 cycle complete" log appended Jun 8, 2026 says
  feature-02's Step 2 will `git mv` "7 `p2_*.py` smokes".
  That count is wrong on **both** axes: (a) there are 13
  `p2_*` files, not 7, and (b) none of them are feature-02
  primary. Feature-02's Step 2 will be a no-op (`git mv`
  zero smokes), same shape as feature-01's Step 2.
- **DR2 — "storage trusts" assertion (Jun 8, 2026 decision).**
  The spec says the `.feature` parent-depth check is **not**
  enforced in `create_file`. Originally proposed as `n/a`;
  user opted to flip to `missing` and write a positive
  assertion: `create_file` succeeds when invoked with a
  parent at depth 1 (below the API-layer minimum of 2).
  This tests the documented trust behaviour rather than
  the absence of enforcement. The same rule will appear
  as `missing` again in feature-05's matrix — there it
  will be tested as a positive *rejection* by the
  testcase-crud route.
- **Spec gaps discovered during Step-1 re-review.** Behaviours
  present in `app/storage.py` but **not** in the spec:
  `move_file` enforces `2..MAX_FOLDER_DEPTH` on the destination
  parent (contradicts the DR2 "storage trusts" framing for
  `create_file`); `delete_file` / `delete_folder` are
  idempotent on missing target; `delete_folder` rejects
  empty parts with `ValueError`; `rename_file` is a no-op on
  same-name; `duplicate_file` rejects same-name-as-source;
  `list_folder` raises `ValueError` on depth > `MAX_FOLDER_DEPTH`;
  `search` returns `[]` for empty queries and rejects `match`
  values other than `"text"` / `"tag"`. **These are not added
  to the matrix** — the audit tests the spec as written.
  They are surfaced here for a follow-up spec patch.
- **AC ↔ rule overlap is heavy** here (much more than
  feature-01). Every AC bullet restates a P/D/A/L/N/S
  rule with a strengthened claim. They are kept as separate
  rows because the additional claim is independently
  testable; Step 4 will collapse them into the same smoke
  file when convenient (`F02_08_acceptance.py`).
- **Three rules need real concurrency assertions.** AC3
  (two threads serialise on the same file), AC4 (no
  deadlock under stress), and LK3 (sorted dual-lock
  acquisition) require threading primitives. These are
  the spiciest gap-fills in the eight-file plan; expect
  `F02_05_locking.py` and the matching `F02_08_acceptance.py`
  rows to be longer than the rest.
- **Self-write rules** (SW1/SW2 + AC5) require a watcher
  / EventBus interaction. The `was_recently_written` public
  API is the assertion surface; we do not need to spin up
  the real watcher to test the self-write bookkeeping
  itself — only AC5's end-to-end claim does.

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-02:

1. **Rule list re-reviewed against spec + code.** 32 rules
   confirmed (PD×4, DR×6 inc. DR3a–d split, AW×4,
   NU×4, LK×3, SW×2, SR×4, AC×5). No additions, no removals.
   Spec gaps found in `storage.py` (move_file dest-depth,
   idempotent deletes, etc.) surfaced in Notes & flags but
   **not** added to the matrix — audit tests the spec as
   written.
2. **DR2 flipped from `n/a` to `missing`.** Step 4 will
   write a positive "storage trusts" assertion: `create_file`
   succeeds at parent depth 1 (below the API minimum).
3. **`IN-PROGRESS.md` correction approved.** Feature-02's
   Step 2 is a no-op `git mv` (zero files to move),
   same shape as feature-01. Same applies to features
   03 – 09; only features 10 / 11 have existing smokes
   to restructure.
4. **Concurrency + watcher assertions pre-approved for
   Step 4.** `F02_05_locking.py` (LK3) and `F02_08_acceptance.py`
   (AC3 / AC4 / AC5) will use real `threading` primitives;
   AC5 will spin up a `Bus`-style subscription to verify
   self-write suppression end-to-end.

Ready for **Step 2 (Restructure)**.

## Step 2 execution log

**Jun 8, 2026** — Step 2 (Restructure) executed for feature-02:

- `git mv` was a no-op: feature-02 had zero existing smokes
  to move (Step-1 audit confirmed).
- Planned filenames assigned per row via replace_all anchored
  on the `Spec § | _(planned)_` cell combo:
  - `F02_01_path_discipline.py` (PD1–PD4, 4 rules)
  - `F02_02_depth_rules.py` (DR1, DR2, DR3a–d, 6 rules)
  - `F02_03_atomic_write.py` (AW1–AW4, 4 rules)
  - `F02_04_name_uniqueness.py` (NU1–NU4, 4 rules)
  - `F02_05_locking.py` (LK1–LK3, 3 rules)
  - `F02_06_self_write.py` (SW1–SW2, 2 rules)
  - `F02_07_search.py` (SR1–SR4, 4 rules)
  - `F02_08_acceptance.py` (AC1–AC5, 5 rules)
- Global prerequisites (`.smoke-scratch/README.md`,
  `.smoke-scratch/run.py`) already exist from feature-01's
  Step 2; no setup work needed.

Next: **Step 3 (Refine)** is a no-op (no existing smokes
to refine). Cycle proceeds directly to Step 4.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-02:

- Eight smoke files written, one per spec section, ~80–220
  lines each:
  - `F02_01_path_discipline.py` covers PD1–PD4 (4 rules).
  - `F02_02_depth_rules.py` covers DR1, DR2, DR3a–d (6 rules).
  - `F02_03_atomic_write.py` covers AW1–AW4 (4 rules).
  - `F02_04_name_uniqueness.py` covers NU1–NU4 (4 rules).
  - `F02_05_locking.py` covers LK1–LK3 (3 rules).
  - `F02_06_self_write.py` covers SW1–SW2 (2 rules).
  - `F02_07_search.py` covers SR1–SR4 (4 rules).
  - `F02_08_acceptance.py` covers AC1–AC5 (5 rules).
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 02 --verbose` reports `8/8 passed; 0 failed`
  and all 32 rule-level `PASS  <id>: …` lines fire.
- Full-suite re-run (`run.py` without filter) reports
  `13/13 passed; 0 failed`, confirming no regression in
  feature-01.
- **Per-rule notes:**
  - **DR2** uses the agreed "storage trusts" positive
    assertion: `create_file` succeeds with a parent at
    depth 1 (below the API-layer minimum of 2).
  - **AW1/AW2/AW3/AC2/AC5** monkey-patch `app.storage.os.replace`
    (and `os.fsync` for AW2) to capture or simulate failure
    around the atomic-write commit point.
  - **AC2** simulates a true crash by snapshotting the
    leaked temp before raising `SimulatedCrash`, then
    re-planting it and running `cleanup_orphan_temp_files`
    to verify boot-scan recovery.
  - **LK1** verifies `_PathLock` weakref-collectability
    by holding a `weakref.ref`, dropping the strong refs,
    running `gc.collect()`, and asserting the entry is
    purged from `_locks`.
  - **LK2/LK3/AC3/AC4** use real `threading` primitives
    (`Barrier`, `Thread`); deadlock checks use a 2–5 s
    timeout per join.
  - **NU2** asserts the exact-name conflict path only;
    case-variation behaviour is host-fs-dependent per
    the spec and intentionally not asserted.
  - **AC5** asserts storage's *half* of the suppression
    contract: (a) every successful mutation marks the
    target as recently-written, and (b) every temp
    filename matches `TEMP_FILE_RE`. The watcher half
    (consuming both contracts) is feature-03's matrix.

**Feature-02 cycle complete.** Per the locked plan,
**feature-03 (watcher-and-sse) is next**. Feature-03 will
likely audit similarly to feature-01 / feature-02 (zero
existing primary-frame smokes; `p2_2e_sse_picks_up_external_change.py`
remains in its feature-10 primary frame but provides incidental
coverage of the change-detection path).
