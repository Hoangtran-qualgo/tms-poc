# In-progress backlog

Items observed during v1 manual verification that still need work. Grouped
by MoSCoW priority. Each entry should grow a short repro and pointer to the
relevant file(s) when picked up.

Convention: all **Investigate**-phase items default to **Should have** or
**Could have**; only file an Investigate item under **Must have** when it
is explicitly designated as such.

## Must have

_(empty)_

## Should have

- **Restructure and extend the `.smoke-scratch/` smoke suite.**
  _Filed Jun 5, 2026 as "Introduce backend test harness (`pytest`)";
  re-scoped Jun 8, 2026 — keep the standalone-script approach, no
  `pytest` (or any other harness) is introduced; plan locked
  Jun 8, 2026 after a five-round clarification pass._ The
  codebase ships ~50 standalone smoke scripts under
  `.smoke-scratch/` produced incrementally during the test-run
  feature's Phase-1/2/3 deliveries, the Jun-8 "Relocate +
  simplify the `+ New run` flow" change, and the Jun-8
  project-level enums feature. Each is one
  `tempfile.TemporaryDirectory` + a fresh `Storage` + a
  sequence of `assert`s + `print("PASS ...")`, runnable as
  `PYTHONPATH=. .venv/bin/python <file>`. The
  one-file-per-scenario discipline stays; no shared
  conftest / fixture machinery is introduced.
  - **Re-scope rationale**: the smoke-script style has worked
    well across three features in a row — each script doubles
    as documentation of one acceptance criterion, the
    failure mode is a stack trace pointing at the exact
    assertion, and re-running a single file is the trivial
    `python <file>` command. A `pytest` harness would add a
    dependency + a fixture layer + a runner concept for no
    behavioural gain.
  - **Locked decisions** (Jun 8, 2026):
    - **Layout**: `.smoke-scratch/feature-<N>/F<N>_<MM>_<spec-section-slug>.py`,
      where `<N>` is the spec feature number from
      `specs/features/<N>-*.md` and `<MM>` zero-padded
      restarts at `01` per directory. Within-directory order
      follows spec-section order so readers can walk the spec
      and the smoke directory in parallel. New smokes append
      at the end of `<MM>`; existing files are never
      renumbered (avoids invalidating cross-file references).
    - **Boilerplate reminder**: a new
      `.smoke-scratch/README.md` documents the canonical
      `make_app()` pattern once. Each smoke carries a single
      top-of-file pointer comment
      (`# Pattern: see .smoke-scratch/README.md`). No
      helper module is introduced; copy-paste stays the rule.
    - **Runner**: one ~50-line `.smoke-scratch/run.py` that
      walks `feature-*/` directories, runs every `F<N>_*.py`,
      and reports per-file `PASS / FAIL` plus an aggregate
      count. Flags: `--filter <feature>` (run one feature
      dir), `--list` (enumerate smokes without running),
      `--verbose` (echo each smoke's stdout). All results are
      reported (no fail-fast); exit non-zero if any smoke
      fails.
    - **Audit rule heuristic**: a "rule" is any imperative
      statement in the spec (`raises`, `rejects`, `stores`,
      `filters`, `emits`, `returns`, …) plus every bullet in
      the spec's Acceptance section. The audit extracts those
      rows into a coverage matrix.
    - **Coverage artifact**: per-feature
      `feature-<N>/COVERAGE.md` with a single markdown table:
      `# | Rule | Spec § | Smoke file | Status` where
      `Status ∈ {covered, missing, n/a}`. No global
      coverage file (would go stale on every feature
      update).
    - **Cross-feature smokes**: place each smoke in the
      primary feature's directory and name the secondary
      feature in the top-of-file comment. Duplicate across
      directories **only** when the two assertions differ in
      shape — identical assertions never duplicate.
    - **Sequencing**: feature-by-feature, end-to-end. Per
      feature, the audit happens at the start of that
      feature's cycle (not a global up-front audit of all
      eleven specs).
    - **Definition of done (per feature)**: every audited
      rule has at least one smoke whose assertion fails when
      the rule is violated. Feature is "done" when its
      `COVERAGE.md` has zero `missing` rows and `run.py
      --filter feature-<N>` is green.
    - **Defaults**: unshipped specs get no directory until
      they ship; the existing-smoke → feature mapping is
      proposed and confirmed before any `git mv`; `git mv`
      is the move command so blame survives.
  - **Per-feature execution cycle**:
    1. **Audit** → produce `feature-<N>/COVERAGE.md` with
       every rule + initial status (mostly `missing`).
       _Verify_: table is complete versus the spec; user
       signs off on the rule list before any file moves.
    2. **Restructure** → `git mv` the current smokes into
       `feature-<N>/`, rename to `F<N>_<MM>_<slug>.py` in
       spec-section order, add the pattern-pointer comment,
       update `COVERAGE.md` Status from `missing` to
       `covered` where applicable.
       _Verify_: `run.py --filter feature-<N>` is green;
       `COVERAGE.md` statuses reflect reality.
    3. **Refine** → tighten assertion messages so a failure
       pinpoints the exact rule violated; drop dead
       `if False:` / commented-out branches; drop any
       `print("PASS  ...")` that does not name a concrete
       rule.
       _Verify_: `run.py --filter feature-<N>` still green;
       diff shows only quality fixes.
    4. **Gap-fill** → write smokes for every remaining
       `missing` row in `COVERAGE.md`.
       _Verify_: `COVERAGE.md` has zero `missing` rows;
       `run.py --filter feature-<N>` green.
    5. **Done** → feature `<N>` is shipped; move on to
       `<N+1>`.
  - **Out of scope**: UI / browser smoke tests stay manual —
    Playwright remains explicitly out of scope per user
    direction. Same-process SSE suppression demos that need
    two browser tabs stay manual.

## Could have

- **Investigate: persist expand-state for the Test run sidebar tab.**
  _Filed Jun 5, 2026 as a Phase-2 follow-up to
  `specs/features/10-feature-test-run-NEW.md`._

  The Directory-tree tab keeps expand state across SSE refreshes
  via `tmsExpandedFolders` + `tmsRestoreTreeState`. The Test-run
  tab is **stateless** in v1: every `sse:change` re-renders it
  with all groups collapsed. Investigate whether runs / groups
  grow enough per project (heuristic: >50) that this becomes
  annoying. If yes, add a sibling Set + restore helper scoped to
  `#test-run-pane`, hooked into `htmx:afterSwap`.

- **Investigate new feature: test report.**
  - Filter test cases by condition (folder / tag / tag-presence
    percentage — e.g., what % of test cases carry tag `@xxx` and
    what % do not).
  - **Rendering**: no pie chart. Render each category as a top-level
    bullet point with a count / percentage, expandable via a
    collapse/expand drop-down that reveals the matching test cases
    underneath. All groups collapsed by default.
  - Deeper reports derived from test runs — scope TBD; nail down
    during the Investigate phase.

- **Investigate new feature: folder-level test case filter.**
  - From a folder view, filter and list test cases by contain /
    not-contain rules over:
    - a specific tag.
    - a specific group of tags (all must match / none must match).
    - any tag within a specific group of tags (at least one matches).
  - Investigate the UX (chip-based filter bar vs. modal), the query
    surface (extension of `GET /api/search` vs. a new endpoint), and
    how it interacts with the existing tree / folder views.

- **Investigate: per-project `enums.yaml` CRUD UI.**
  _Deferred from `11-feature-testcase-component` v1 (Jun 8, 2026)._
  - Add / remove an enum kind, add / remove entries within a
    kind, rename a key with cascade across affected `.feature`
    files (rewrite every `# enum.<kind>: <old_key>` directive
    to `# enum.<kind>: <new_key>` atomically).
  - SSE-driven live refresh of in-session picker caches —
    lands together with the CRUD UI since the two share the
    invalidation path.
  - Out of scope until v1 of `11-feature-testcase-component`
    ships and teams start hitting the limits of the
    hand-edit-the-YAML flow.

- **Investigate new feature: quality report.**
  - In a project, list the most-failed areas based on component data
    in the selected test run (max. 10).
  - In a project, list the per-test-case statistic in the selected
    test run (max. 10).
  - Depends on the `component` data investigation above.

