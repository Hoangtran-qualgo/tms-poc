# 20 · Import auto-generated test-case filenames

_**SHIPPED Aug 19, 2026.** Additive follow-up to features 14 and 17. Changes
only the import preview's filename defaults; request and storage behaviour are
unchanged._

## Goal

Prefill every import-preview filename with the selected destination folder's
name plus its next available integer:

```
<folder name>_<num>.feature
```

Examples for destination folder `chat`:

```
chat_1.feature
chat_2.feature
chat_3.feature
```

The imported scenario title, Feature title, and browser source filename do not
participate in filename generation.

## Evidence

- The import modal already renders one editable `input[data-role="filename"]`
  per flattened scenario in `app/static/03_folder_actions.js`. It now
  pre-fills the generated value and sends the value unchanged as `names`.
- `/api/tree` is already fetched before the modal opens. Its selected folder
  node has direct file and folder children, so the client can calculate a
  suggestion without a new route or request field.
- `POST /api/files/import` maps `names[i]` to the stable flattened
  source/scenario order. `Storage.import_feature_cases()` remains the only
  authority for leaf normalisation, case-insensitive direct-folder conflicts,
  and all-or-nothing writes.
- Storage permits spaces and the destination folder's existing valid segment
  characters in a feature leaf, while rejecting only the shared forbidden path
  characters. Reusing the folder name verbatim therefore matches existing
  path semantics; no slugifier is needed.

## Confirmed contract

1. **Stem:** use the selected destination folder's final path segment exactly.
   For destination `project/API/Workspaces`, the stem is `Workspaces`.
2. **Number:** begin at `1` and choose the smallest unused positive integer.
   A name is unavailable when a direct child file or folder has the same leaf
   name, using case-insensitive comparison.
3. **Batch order:** assign the available names in the existing flattened
   source/scenario order. A three-scenario import into an empty `chat` folder
   pre-fills `chat_1.feature`, `chat_2.feature`, and `chat_3.feature`.
4. **Existing names:** if `chat_1.feature` and `chat_3.feature` already exist,
   the first two suggestions are `chat_2.feature` then `chat_4.feature`. A
   matching folder leaf also reserves that number because storage does so.
5. **User control:** suggestions prefill the existing inputs and remain
   editable. Import stays gated on non-empty names and storage revalidates all
   final values at commit time.
6. **Destination change:** regenerate only fields still holding a generated
   value when the user selects a different destination folder; never overwrite
   a manual edit.

## Implementation record

- `tmsSuggestImportFilenames()` in `app/static/03_folder_actions.js` produces
  sequential candidates from a folder leaf plus occupied direct-child names.
- The import modal indexes the already-fetched tree by path. After preview and
  after a project/destination change, it refreshes generated fields while
  preserving any manually edited field.
- No parser, route, request, or storage changes were needed.
- `feature-20/F20_01_folder_sequence_filenames.py` executes the production
  helper for starts, gaps, case-insensitive reservations, and canonical-name
  handling; it also locks tree lookup, edit-preservation, and commit wiring.
  Feature-17 (2/2) and feature-14 (4/4) compatibility checks pass.

## Blindspot

The tree snapshot can become stale if another user/process writes a matching
filename after preview. The storage pre-flight remains authoritative and will
abort the complete import instead of overwriting a case. Retrying with fresh
suggestions is a separate UX decision.

Availability compares exact canonical leaf names only. For example, an existing
`chat_01.feature` does not reserve the generated `chat_1.feature`; parsing
arbitrary legacy numeric suffixes would add complexity without changing the
storage conflict rule.

## Affects

- `app/static/03_folder_actions.js` — destination-folder sequence suggestion
  and edit-preservation logic beside existing import rows.
- `.smoke-scratch/feature-17/` — focused client contract coverage; feature-14
  keeps legacy one-source compatibility covered.

## Depends on

- Feature 14's editable output-name fields and storage-side name validation.
- Feature 17's deterministic flattened source/scenario ordering and batch
  transaction.

## Surface for follow-up

- Server-issued filename reservations would need a concurrency/expiry design;
  this proposal intentionally retains the client prefill and existing storage
  guard.
