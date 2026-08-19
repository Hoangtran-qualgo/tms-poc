# 19 · Enum inline create and kind labels

_Shipped Aug 17, 2026. Extends feature 13 without changing stable kind IDs,
feature directives, enum-ranking reports, or the existing enum API shape._

## Goal

Make enum creation an inline manager flow and let a user change a kind label.

## Evidence before implementation

- `tmsEnumsManager._addKind()` and `_addEntry()` used native prompts. Entry
  labels are already editable inline and persist through `PUT /api/enums`.
- `read_project_enums()` returns `{kind_id: {entry_key: entry_label}}` and
  validates the same shape on write. There is no distinct persisted kind
  label in `enums.yaml`, the API response, or the manager state.
- `Feature.enums` persists kind IDs in `# enum.<kind_id>: <entry_key>`;
  `_cross_check_enums` resolves those IDs against `enums.yaml`.
- `enum_ranking` reports also persist `kind` and require it to resolve in the
  project vocabulary. An identifier rename therefore reaches features and
  report YAML files, while a display-label change need not.
- Existing project vocabularies contain IDs such as `components`, `sprint`,
  and `knowledge`, with no separate kind labels.

The runnable spike
`.smoke-scratch/_investigate/enums-create-label/01_kind_identity.py` confirms
the schema, serialized feature directive, and stable-ID/label separation.

## Confirmed contract

### D1 · Inline creation covers kinds and entries

`+ Add kind` opens inline **Kind ID** and **Kind label** fields. `+ Add entry`
opens inline **Entry key** and **Entry label** fields inside its kind section.
Both use existing client validation, update manager memory only, and persist
with the existing Save action. Native prompts remain only for unrelated key
rename.

### D2 · Kind label is display metadata; kind ID stays stable

`enum-kind-labels.yaml` is an optional project-root mapping of kind ID to
display label. It is separate from `enums.yaml`, preserving the established
`{kind_id: {entry_key: entry_label}}` schema and the bare-vocabulary response
of `GET /api/enums/<project>`. Missing metadata, or a label equal to its ID,
displays the stable ID; legacy projects need no migration. The manager uses
the label in its editable kind header and keeps the ID visible beside it.

`PUT /api/enums/<project>/kind-labels` accepts a full map containing exactly
the current kinds, validates non-empty single-line labels, and returns the
resolved map. Removing a kind through the existing vocabulary write prunes its
metadata; Clear deletes the sidecar with the vocabulary reset.

No `.feature` directive or enum-ranking report is rewritten. Their kind IDs
remain stable by contract.

## Accepted blindspot

Save first writes the existing vocabulary, then display-label metadata. Those
two files cannot be one plain-filesystem transaction. If the second request
fails, kinds/entries are already saved and their display labels safely fall
back to IDs; retrying Save completes metadata persistence. Labels are exposed
in the manager only; other existing ID-based views remain unchanged.

## Implementation record

1. `Storage.read_project_enum_kind_labels()` resolves every current kind to a
   saved label or stable-ID fallback. `write_project_enum_kind_labels()`
   validates/writes the sidecar and omits default-equals-ID labels on disk.
2. The new label PUT route is additive. Existing `GET`/`PUT /api/enums` and
   all `{kind_id: {key: entry_label}}` consumers remain unchanged.
3. `tmsEnumsManager` receives labels in its UI payload, exposes editable kind
   labels, and replaces both creation prompt flows with inline forms.
4. Feature-19 smoke coverage proves stable feature directives, legacy
   fallback, removed-kind/Clear cleanup, label API validation, manager payload,
   inline forms, and retained ID/key validation.

## Affects

- `app/templates/enums_manager.html` and `app/static/08_enums_manager.js` —
  current create controls and kind headings.
- `app/storage/_core.py`, `app/storage/_enums.py`, and
  `app/server/routes_enums.py` — additive sidecar metadata and label PUT.
- `Feature.enums`, `app/gherkin_io.py`, and enum-ranking report persistence —
  verified unchanged because their stable kind IDs do not change.

## Depends on

- Feature 13's validated whole-vocabulary write and Clear lifecycle.
- Feature 11's stable kind ID directive and test-case cross-check.
- Feature 12's enum-ranking `kind` persistence, left untouched by labels.

## Surface for follow-up

- Kind-ID rename remains a separate cascade feature because it reaches feature
  directives and enum-ranking reports.
- Localized labels, labels shared across projects, and propagation of display
  labels to other existing ID-based views remain separate.
