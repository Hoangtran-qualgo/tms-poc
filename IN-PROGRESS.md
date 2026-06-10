# In-progress backlog

Items observed during v1 manual verification that still need work. Grouped
by MoSCoW priority. Each entry should grow a short repro and pointer to the
relevant file(s) when picked up.

Convention: all **Investigate**-phase items default to **Should have** or
**Could have**; only file an Investigate item under **Must have** when it
is explicitly designated as such.

## Must have

_(empty)_

_The five UI/UX styling + detailing enhancements (E1–E5) specced in
`specs/tech/02-tech-ui-styling-enhancement-NEW.md` shipped Jun 10, 2026 —
see `DONE.md` for the as-built breakdown._

## Should have

_(empty)_

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

- **Investigate new feature: folder-level test case filter.**
  - From a folder view (from project/ level to single folder level), filter and list test cases by contain /
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

