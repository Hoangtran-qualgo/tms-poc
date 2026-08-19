# 16 · Recursive test-case counts in directory tree

_Shipped Aug 10, 2026. Product counting rules and numeric folder metadata
shape confirmed._

## Goal

Show aggregate test-case counts beside each directory-tree folder name, from
project / module nodes through nested branch nodes. Display shape:

```text
desktop-app (100-80-20)
```

The three values are, in order: total scenarios in the folder subtree,
scenarios carrying tag `@auto`, and scenarios without that tag. The third
value is derived as `total - auto`.

## Implementation context

- `Storage.list_tree()` aggregates counts during its recursive folder/file
  walk (`app/storage/_listing.py`).
- `tree.html` renders each visible folder's count; caret, path, and HTMX
  navigation remain separate hooks.
- Tree refresh is whole-tree on initial render, SSE change, or manual refresh;
  count freshness follows that existing path.
- Tags are bare model strings. `Examples:` tags are not first-class surfaces
  and do not affect this feature.
- Normal TMS writes keep one scenario per `.feature`, but import and external
  files can expose multiple scenarios; counting tolerates those sources.

## As-built (Do-1 through Do-3)

- `Storage.list_tree()` now aggregates scenario counts in one recursive walk.
- Every visible folder node, including project nodes, carries numeric `counts`.
- `tree.html` renders `(total-auto-non_auto)` beside project/module/branch
  names.
- Focused smokes `F16_01_storage_counts.py` and
  `F16_02_tree_template.py` pass (2/2).

## Proposed rules (pending confirmation)

### Counting

- Count scenarios recursively beneath each displayed folder, including
  scenarios in files directly inside that folder and in descendant branches.
- Include project, module, and every visible nested branch node. Root wrapper
  has no displayed count.
- For parseable files, total = number of scenarios. If feature-level tags
  contain `auto` case-insensitively, all scenarios count as auto. Otherwise,
  only scenarios whose scenario-level tags contain `auto` count as auto.
- A malformed/unreadable `.feature` contributes one total, one non-auto, and
  zero auto so visible files remain represented.
- Matching is exact after case folding (`Auto` matches `auto`), not substring.
- `non_auto = total - auto`; counts must satisfy `total == auto + non_auto`.
- Typed areas hidden from the directory tree (`test-run`, `report`) and
  hidden project metadata (`enums.yaml`) do not contribute.

### Data shape

Preferred storage wire addition on every folder node:

```json
"counts": {"total": 100, "auto": 80, "non_auto": 20}
```

File nodes remain unchanged. The UI formats this object as
`(<total>-<auto>-<non_auto>)`; storage/API callers retain numeric values.

### Error and freshness behavior

- Use the pure Gherkin splitter for tag/scenario extraction, avoiding project
  enum cross-checks during tree enumeration.
- Parse failures do not break tree rendering. They contribute one total and
  one non-auto under the confirmed fallback; auto count remains zero.
- Compute counts during the existing recursive tree walk. Do not add a cache
  or watcher protocol: SSE/manual refresh already refetches the whole tree.
- Preserve folder ordering, folder-hoisting, temp-file filtering, reserved
  area filtering, row `data-path`, caret behavior, and HTMX navigation.

## Confirmed edge handling

- Folder nodes carry numeric `counts`; the UI formats the compact label.
- A source with no parseable scenarios contributes one total and one
  non-auto. This keeps malformed visible files represented without inventing
  tag data.

## Implementation slices

1. **Storage:** extend the existing `_tree_children` post-order walk to return
   scenario counts and attach `counts` to every visible folder node; parse
   each feature once per tree build with `split_feature_source()`.
2. **Template:** render the compact suffix beside `child.name`, preserving
   existing navigation and expand-state markup.
3. **Smokes:** assert nested roll-up, tag levels, malformed files, reserved
   areas, invariant arithmetic, and tree template wiring.
4. **Check / Act:** feature-16 smokes pass; full suite has six unrelated
   macOS watchdog `fsevents` failures, all existing watcher acceptance paths.

## Affects

- `app/storage/_listing.py` — computes aggregate counts while building the
  recursive tree.
- `app/templates/tree.html` — displays counts beside folder names at every
  visible depth.
- `app/server/routes_tree.py` — exposes enriched tree JSON through existing
  `GET /api/tree` without a new endpoint.
- `specs/features/06-feature-tree-pane-NEW.md` — tree node contract and
  acceptance criteria need a confirmed count extension.
- `specs/features/07-feature-folder-views-NEW.md` — folder navigation remains
  unchanged; count semantics must stay aligned with folder depth.
- `03-feature-watcher-and-sse` — no protocol change, but existing refresh
  freshness becomes part of count behavior.

## Depends on

- `01-feature-gherkin-io` — parser/model tag normalization and parse errors.
- `02-feature-storage-core` — logical paths, tree traversal, temp filtering,
  and reserved typed-area rules.
- `06-feature-tree-pane` — recursive folder row structure and SSE/manual
  whole-tree refresh.
- `README.md` — feature/scenario tag surface and Examples-tag limitation.
- Existing invariant that normal TMS writes contain one scenario per
  `.feature`; tolerant counting must still handle external/multi-scenario
  source without changing write invariants.

## Surface for follow-up

- Makes future scenario-count chips, percentages, and configurable tag
  counters possible from one numeric folder-node contract.
- Full-tree parsing adds per-refresh work; current design is acceptable for
  small local trees but may need incremental aggregation or a cache for very
  large roots.
- If users need multiple tracked tags, replace fixed `auto` field with a
  tag-counter map; do not broaden v1 silently.
- Malformed-file handling may need a separate warning count later; v1 keeps
  tree visibility and count arithmetic deterministic.

## Acceptance criteria (after confirmation)

- Every visible folder row renders `(<total>-<auto>-<non_auto>)` beside its
  name; file rows and root wrapper do not.
- Counts roll up recursively and satisfy `total == auto + non_auto`.
- `@auto` classification follows confirmed tag source and case rule.
- External edits / creates / deletes update counts on the existing tree SSE
  refresh; manual refresh also updates counts.
- Existing caret, expansion persistence, navigation, reserved-area hiding,
  and folder/file ordering remain unchanged.
- Focused smokes and full smoke suite pass; browser pass confirms nested rows
  remain readable.
