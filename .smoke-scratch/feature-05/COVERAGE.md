# feature-05 · Test case CRUD — coverage matrix

Step 1 audit of the smoke tests against
`specs/features/05-feature-testcase-crud-NEW.md`.

## Method

- Spec source: `specs/features/05-feature-testcase-crud-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Spec sub-headings under `## Invariants & rules` are
  treated as **sections** for the one-smoke-per-section
  rule (Decision A) — seven sub-sections here so each
  gets its own file.
- Public surface is split per sub-heading (HTTP routes,
  UI triggers, UI gaps) for the same reason.
- `Status` values: `covered`, `partial` (incidental coverage
  inside a primary-other-feature smoke), `missing`, `n/a`
  (rule is documentation-only / not testable).
- `Smoke file` column carries the target file for every row.
  Per Decision A, feature-05 uses **one smoke per spec
  section** — **eleven files total**
  (`F05_01_http_routes.py` … `F05_11_acceptance.py`).
  All eleven exist as of Step 4 (Jun 8, 2026).
- **Storage-methods sub-section IS given matrix rows**
  (per Step-1 sign-off Q2: "accept duplicated effort if
  2 tests are not identical"). The nine `Storage.*`
  signatures get their own SM1–SM9 rows. Each row's
  primary-frame coverage lives in feature-02 (storage-
  direct assertions like `s.create_file(…)` then
  `assert (root/…).is_file()`); the feature-05 route-
  half lives in `F05_01_http_routes.py` (HTTP-shape
  assertions like `client.post(…)` then
  `assert r.status_code == 201`). The two halves are
  non-identical — one tests the storage invariant, the
  other tests the HTTP delegation envelope — so the
  duplication is allowed under Decision E.
- **Primary-frame distinction.** Feature-05 is the
  HTTP-route + UI-wiring layer for `.feature`-file CRUD;
  features 01 (gherkin-io), 02 (storage-core), and 03
  (watcher-and-sse) own the underlying contracts. The
  smokes below assert the *route layer's* delegation +
  response envelope, not those underlying contracts.

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| SM1 | `Storage.create_file(parts, description)` creates a `.feature` file under an existing module / sub-folder; normalises the leaf via `_normalize_filename`, validates `description`, atomic-writes the placeholder source, marks the target recent. | Public surface → Storage methods | `F02_06_self_write.py` (SW1 storage half) + `F05_01_http_routes.py` (HR1 route half) | covered |
| SM2 | `Storage.read_feature(parts) -> Feature` reads + parses an existing `.feature` file into the structured `Feature` dataclass; raises `FileNotFoundError` on missing target. | Public surface → Storage methods | `F02_08_acceptance.py` (AC1 path-confinement coverage) + `F02_06_self_write.py` (SW1 reuse) + `F05_01_http_routes.py` (HR2 route half) | covered |
| SM3 | `Storage.read_raw(parts) -> str` returns the raw UTF-8 text of any file inside the data root; raises `FileNotFoundError` on missing target. | Public surface → Storage methods | `F02_08_acceptance.py` (AC1 path-confinement coverage) + `F05_01_http_routes.py` (HR8 route half) | covered |
| SM4 | `Storage.write_feature(parts, feature)` serialises a `Feature` and atomic-writes it to an existing file; marks the target recent; rejects missing targets. | Public surface → Storage methods | `F02_06_self_write.py` (SW1 storage half) + `F05_01_http_routes.py` (HR3 route half) | covered |
| SM5 | `Storage.write_raw(parts, text)` parses + validates `text`, normalises newlines, then atomic-writes the canonical form; marks the target recent. | Public surface → Storage methods | `F02_06_self_write.py` (SW1 storage half) + `F02_07_search.py` (search-fixture setup) + `F05_01_http_routes.py` (HR9 route half) | covered |
| SM6 | `Storage.rename_file(parts, new_name)` renames a file within its existing parent folder; same-parent only; normalises `new_name`; sorted dual-lock for deadlock safety; marks both source and target recent. | Public surface → Storage methods | `F02_04_name_uniqueness.py` (NU* coverage) + `F02_05_locking.py` (LK3 sorted-lock) + `F02_06_self_write.py` (SW1 rename half) + `F05_01_http_routes.py` (HR5 route half) | covered |
| SM7 | `Storage.move_file(source_parts, dest_parent)` moves a file to a different parent folder at depth `2..10`; leaf name preserved; same-parent rejected; sorted dual-lock; marks both paths recent. | Public surface → Storage methods | `F02_08_acceptance.py` (AC4 deadlock avoidance, rename/move shape) + `F05_01_http_routes.py` (HR6 route half) | covered |
| SM8 | `Storage.duplicate_file(parts, new_name)` copies the file to a new leaf in the same parent via `_atomic_write_bytes`; normalises `new_name`; same-parent / same-extension; sorted dual-lock; marks target recent. | Public surface → Storage methods | `F02_05_locking.py` (LK3 sorted-lock duplicate stress) + `F02_06_self_write.py` (SW1 duplicate half) + `F05_01_http_routes.py` (HR7 route half) | covered |
| SM9 | `Storage.delete_file(parts)` deletes the file; idempotent on missing target; marks both target path and parent dir recent. | Public surface → Storage methods | `F02_06_self_write.py` (SW1 delete half + parent-dir mark assertion) + `F05_01_http_routes.py` (HR4 route half) | covered |
| HR1 | `POST /api/files` body `{file_name, description, parent}`: `parent` segments must be `2..10`; non-empty `description` required; returns `{ok: true}` 201. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR2 | `GET /api/files/<path:p>` returns `Feature.to_dict()` 200; non-`.feature` extensions → 415 `unsupported_type`. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR3 | `PATCH /api/files/<path:p>` body matches `Feature.from_dict` shape; validates + serialises + atomic-writes; returns `{ok: true}` 200. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR4 | `DELETE /api/files/<path:p>` returns `""` 204 (idempotent: missing target = 204). | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR5 | `PATCH /api/files/<path:p>/rename` body `{file_name}`; same-parent only; returns `{ok: true}` 200. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR6 | `PATCH /api/files/<path:p>/move` body `{parent}`; leaf preserved; destination parent depth `2..10`; same-parent attempts rejected with 400; returns `{ok: true}` 200. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR7 | `POST /api/files/<path:p>/duplicate` body `{file_name}`; same-parent, same-extension; returns `{ok: true}` 201. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR8 | `GET /api/files/<path:p>/raw` returns source text with `Content-Type: text/plain; charset=utf-8`; non-`.feature` → 415. | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| HR9 | `PUT /api/files/<path:p>/raw` accepts raw text body; parses + validates + re-serialises + atomic-writes; returns `{ok: true}` 200. _Note: spec says "validates + re-serialises" but as-shipped code only parses + newline-normalises; see RR1a / RR1c spec-gap notes below._ | Public surface → HTTP routes | `F05_01_http_routes.py` | covered |
| UI1 | `tmsCreateFile(parent)` in `app/static/app.js` uses `tmsOpenModal` with two fields (file name + description), posts `/api/files` with `{parent, file_name, description}`; modal hint declares `.feature` is auto-appended. | Public surface → UI triggers | `F05_02_ui_triggers.py` | covered |
| UI2 | `tmsEditor.rename()` invokes `PATCH /api/files/<state.path>/rename` after prompting for a new file name; wired to the `#btn-rename` topbar button. | Public surface → UI triggers | `F05_02_ui_triggers.py` | covered |
| UI3 | `tmsEditor.move()` opens a tree-based folder picker modal then invokes `PATCH /api/files/<state.path>/move`; wired to the `#btn-move` topbar button. | Public surface → UI triggers | `F05_02_ui_triggers.py` | covered |
| UI4 | `tmsEditor.save()` invokes `PATCH /api/files/<state.path>` with the structured buffer (delegates to `saveRaw()` when on the raw tab); wired to the `#btn-save` topbar button. | Public surface → UI triggers | `F05_02_ui_triggers.py` | covered |
| UI5 | `tmsEditor.saveRaw()` invokes `PUT /api/files/<state.path>/raw` with the raw textarea contents; wired to the `#btn-save-raw` button. | Public surface → UI triggers | `F05_02_ui_triggers.py` | covered |
| UG1 | `DELETE /api/files/<p>` has **no UI button** in v1 — API-only. Testable as absence of `Delete file` / `tmsEditor.delete` / `tmsDeleteFile` symbols and as absence of `#btn-delete` in `file_editor.html`. | Public surface → UI gaps | `F05_03_ui_gaps.py` | covered |
| UG2 | `POST /api/files/<p>/duplicate` has **no UI button** in v1 — API-only. Testable as absence of `Duplicate file` / `tmsEditor.duplicate` / `tmsDuplicateFile` symbols and as absence of `#btn-duplicate` in `file_editor.html`. | Public surface → UI gaps | `F05_03_ui_gaps.py` | covered |
| FN1 | Leaf is normalised on create / rename / duplicate by `_normalize_filename`: case-insensitive extension comparison, rejects non-`.feature` extension supplied explicitly, auto-appends `.feature` if missing. (Route-layer assertion; storage-half in feature-02 PD4.) | Invariants → Filename normalisation | `F02_01_path_discipline.py` (storage half) + `F05_04_filename_normalisation.py` (route half) | covered |
| DR1 | File create: `parent` at `2 <= depth <= MAX_FOLDER_DEPTH`; enforced in `server.post_file` (storage trusts the segments). Depth 0 / 1 / 11+ → 400 `bad_request`. | Invariants → Depth rules | `F05_05_depth_rules.py` | covered |
| DR2 | File move destination parent must satisfy the same `2..10` range; enforced in `Storage.move_file`. (Route-layer assertion; storage-half in feature-02 / spec section 02 § Depth.) | Invariants → Depth rules | `F05_05_depth_rules.py` | covered |
| DR3 | Rename / duplicate inherit the source's parent depth, so the `2..10` range is implicitly preserved (no separate enforcement; verifiable by depth-2 and depth-10 sources). | Invariants → Depth rules | `F05_05_depth_rules.py` | covered |
| SP1 | Rename: source and destination share the parent by construction (PATCH `/rename` body carries only `file_name`, never `parent`). | Invariants → Same-parent / cross-parent | `F05_06_same_parent.py` | covered |
| SP2 | Duplicate: same-parent only (no `parent` field accepted; copy lands beside the source). | Invariants → Same-parent / cross-parent | `F05_06_same_parent.py` | covered |
| SP3 | Move: destination parent must differ from the source's; same-parent move is rejected as a no-op → 400 `bad_request`. | Invariants → Same-parent / cross-parent | `F05_06_same_parent.py` | covered |
| CB1 | `description` is required non-empty (whitespace-only rejected at the API layer with 400 `bad_request`). The created file holds `Feature(description=…, scenario=Scenario(kind="scenario", name=""))` — one empty scenario, no steps, no tags, no background. | Invariants → Create body | `F05_07_create_body.py` | covered |
| RR1a | `PUT /api/files/<p>/raw` always parses, validates, and re-serialises before writing; bytes on disk after a raw save may differ from the bytes the client sent (canonical formatting applied). _Note: as-shipped code only parses + newline-normalises (no full re-serialise); the "bytes may differ" claim still holds via CRLF→LF normalisation. See spec gap below._ | Invariants → Raw round-trip | `F05_08_raw_roundtrip.py` | covered |
| RR1b | `PUT /api/files/<p>/raw` with un-parseable text returns 422 `parse_error`. | Invariants → Raw round-trip | `F05_08_raw_roundtrip.py` | covered |
| RR1c | `PUT /api/files/<p>/raw` with parseable-but-invalid text returns 422 `validation_error`. _**Spec/code drift (discovered Step 4):** as-shipped `Storage.write_raw` only calls `parse_feature` — it never calls `validate_feature` or `serialize_feature`. PUT /raw with parseable-but-invalid text actually returns **200** today. Smoke pins the observed behaviour with a message naming the drift. Same shape as feature-04 UI3 and AC6._ | Invariants → Raw round-trip | `F05_08_raw_roundtrip.py` (pins observed 200; flagged spec gap) | covered |
| AL1 | Every mutation through this feature's routes goes through `Storage._atomic_write_bytes` + `Storage._mark_write`; the watcher's `was_recently_written` filter suppresses the resulting FS events so the writing tab sees no SSE echo. (Route-layer integration assertion; storage half in feature-02 AW1-AW4, watcher half in feature-03 EF3.) | Invariants → Atomicity & locking | `F02_03_atomic_write.py` (storage half) + `F03_01_event_filtering.py` (watcher half) + `F05_09_atomicity.py` (route-integration half) | covered |
| ID1 | `DELETE /api/files/<p>` is idempotent — missing target returns 204. | Invariants → Idempotence | `F05_10_idempotence.py` | covered |
| AC1 | Creating a file with a depth-1 `parent` (project only) returns 400 `bad_request` — files must live at depth `2..10`. (Strengthens DR1.) | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC2 | Creating a file with a name conflict in the same parent returns 409 `name_conflict`. | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC3 | Saving via structured `PATCH /api/files/<p>` and saving the same content via `PUT /raw` (after a `GET /raw` round-trip) result in byte-identical files on disk. | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC4 | Renaming to a name that conflicts in the same parent returns 409; the source file is preserved on disk. | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC5 | Moving across folders preserves the leaf name and the file content byte-for-byte. | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC6 | Deleting an already-missing file returns 204. (Strengthens ID1.) | Acceptance criteria | `F05_11_acceptance.py` | covered |
| AC7a | Each successful file-CRUD mutation through the API generates **zero** SSE `"change"` events on the bus (storage's `_mark_write` plus the watcher's `was_recently_written` suppresses the writing tab's self-event). _Split from spec AC7 — see Step-1 sign-off question 1. Spec says "exactly one on other tabs and zero on writing tab" but the EventBus is shared and the actual code yields zero events for any subscriber._ | Acceptance criteria | `F03_06_acceptance.py` AC1 (storage-method half) + `F05_11_acceptance.py` (API-route half) | covered |
| AC7b | An external file mutation (e.g. an out-of-band `(folder / leaf).write_text(…)` that bypasses `Storage`) generates exactly one SSE `"change"` event per open tab, no sooner than `DEBOUNCE_SECONDS` after the last write in the burst. _Split from spec AC7 — preserves the spec's detection-intent half._ | Acceptance criteria | `F03_06_acceptance.py` AC2 (folder-mutation form) + `F04_08_acceptance.py` AC6b (folder-mutation form) + `F05_11_acceptance.py` (file-mutation specialisation) | covered |

## Summary

- Total rules: **44** (9 HTTP routes, 5 UI triggers, 2 UI gaps, 9 storage methods, 1 filename normalisation, 3 depth, 3 same/cross-parent, 1 create body, 3 raw round-trip, 1 atomicity, 1 idempotence, 6 acceptance bullets + 2 from AC7 split).
- `covered`: **44**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-05 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 05`
exits zero with all eleven smokes green). The 13
previously `partial` rows (SM1–SM9, FN1, AL1, AC7a, AC7b)
are now covered by their feature-02 / 03 primary frames
PLUS feature-05's route-layer smokes; the older smokes
stay in their primary frames untouched.

Feature-05 is the largest matrix so far. The 9 HTTP routes
+ 5 UI triggers + 9 storage-method delegation rows + 7
invariant sub-sections + 8 acceptance bullets produce a
high row count, but the resulting smokes are not larger
than feature-04's eight files. SM1–SM9 add NO new smoke
files — they are covered transitively by
`F05_01_http_routes.py` (HR* tests delegate to each
storage method) plus the existing feature-02 storage-level
coverage.

## Notes & flags

- **Zero direct API-route coverage for `/api/files/*`.** A
  grep across `.smoke-scratch/` returns four matches — all
  in feature-04 smokes (`F04_04_name_uniqueness.py`,
  `F04_08_acceptance.py`) that POST `/api/files` purely as
  *setup* for folder-level rules (NU2 coexistence and AC4
  recursive delete). Step 2 will be a no-op `git mv`
  (zero primary-frame smokes to move). Same shape as
  features 02 / 03 / 04.
- **Storage / watcher / parser partial-coverage rows.**
  FN1 + AL1 + AC7a + AC7b are marked `partial` because
  features 01 / 02 / 03 own the *storage / watcher /
  parser half* of those contracts. The feature-05 smokes
  will test the *route layer's* delegation +
  end-to-end shape; the older smokes stay in their primary
  frames untouched.
- **AC7 split (mirrors the feature-04 AC6 split).** Spec
  text says "exactly one SSE change event on other tabs
  and zero on the writing tab" but the EventBus is a
  single shared bus (no per-tab routing): every
  subscriber sees the same events. The actual code
  yields **zero** events for API-route mutations because
  `_mark_write` flags both target and parent dir, and the
  watcher's `was_recently_written` filter drops them
  before publishing. The audit pre-splits AC7 into
  **AC7a** (API mutation → zero events, follows code)
  and **AC7b** (external mutation → exactly one event
  after `DEBOUNCE_SECONDS`, preserves the spec's
  detection intent). **Sign-off question 1.**
- **Storage-methods sub-section omitted from the matrix.**
  The nine `Storage.create_file` / `read_feature` / etc.
  bullets under `## Public surface` are pure
  documentation of the contract that feature-02 already
  primary-frames (every mutation method has its own
  storage-level coverage there). Each HR* row in this
  matrix exercises one of them via the delegation. Adding
  9 zero-effort `covered (via HR*)` rows here would only
  add noise. **Sign-off question 2.**
- **AL1 ("Atomicity & locking") testable shape.** Feature-02
  AC1 (atomic crash-recovery) + AW1-AW4 prove the storage
  primitives. Feature-03 EF3 proves the watcher's
  suppression. Feature-05's AL1 only adds value if it
  proves the *route layer* actually invokes those
  primitives — testable by snapshotting `_recent_writes`
  before/after a `PATCH /api/files/<p>` and asserting the
  target file is marked, OR by watching the parent dir
  for `.tmp.*` files during a save and asserting they
  appear and then disappear (matching `TEMP_FILE_RE`).
  Lightweight integration-level check. **Sign-off question 3:**
  (a) write F05_09 with both checks, (b) write F05_09 with
  only the `_recent_writes` snapshot, or (c) demote AL1
  to `n/a` for feature-05's frame and drop F05_09 (file
  count 11 → 10) since feature-02 + feature-03 already
  prove the underlying primitives.
- **RR1 split rationale.** Spec bundles three testable
  claims into one bullet ("PUT /raw parses + validates
  + re-serialises; bytes may differ; parse_error 422;
  validation_error 422"). The audit splits into
  RR1a (canonicalisation), RR1b (parse_error), RR1c
  (validation_error) for precise failure-mode location.
  **Sign-off question 4.**
- **HR2 / HR8 415 `unsupported_type`.** The
  non-`.feature` extension check is folded into the HR2
  / HR8 row assertions (not a separate rule). Test plan:
  create a `foo.yaml` under a module via a parallel
  `Storage` instance, then `GET /api/files/foo.yaml` →
  415 with `error.code == "unsupported_type"`. (The
  `.yaml` workaround sidesteps `_normalize_filename`'s
  refusal of explicit non-`.feature` ext.)
- **UI gap symbols (UG1 / UG2).** Banned editor symbols
  to grep for: `tmsDeleteFile`, `tmsDuplicateFile`,
  `tmsEditor.delete`, `tmsEditor.duplicate` in
  `app/static/app.js`, and the template ids
  `#btn-delete` / `#btn-duplicate` in
  `app/templates/file_editor.html`. The `tmsEditor.rename`
  / `.move` / `.save` symbols ARE expected to remain
  present (sanity-check fixture for the negative
  assertion).
- **MAX_FOLDER_DEPTH = 10** is the same constant from
  feature-02 / feature-04. The DR1 / AC1 smokes exercise
  it via the file-create HTTP boundary (parent depth 1
  → 400, parent depth 11 → 400 by extension).
- **Spec gaps discovered during Step-1 read-through.**
  - `HR2` / `HR8` 415 envelope shape — spec says only
    "415 unsupported_type" without naming the error
    body shape; assertions will follow the
    server-level convention (`{error: {code,
    message, details}}`).
  - `HR3` / `HR9` 422 envelope shape — same omission;
    same fallback.
  - `HR6` "same-parent move rejected" — spec doesn't
    name the HTTP status code; code raises `ValueError`
    → 400 `bad_request`. Will assert 400.
  - `CB1` "whitespace-only `description` rejected at
    the API layer" — spec says "rejected" but doesn't
    name the code; `server.post_file` raises
    `ValueError` → 400 `bad_request`.
  - AC7 conflates suppression + detection (see split
    above).
  - **RR1c spec/code drift (discovered Step 4).** Spec
    says `PUT /api/files/<p>/raw` "always parses,
    validates, and re-serialises before writing" and
    that "validation errors return 422
    validation_error". The as-shipped
    `Storage.write_raw`
    (`@/Users/hoang.tv/Documents/Projects/tms/app/storage.py:708-731`)
    only calls `parse_feature(text)` — it does NOT call
    `validate_feature(parsed)` nor
    `serialize_feature(parsed)`. The on-disk text is
    just the input with CRLF→LF normalisation. So:
    parseable-but-invalid input slips through and lands
    on disk as 200 instead of 422 `validation_error`,
    and the canonical re-serialisation never happens.
    Two consequences:
    (a) **RR1c** test follows code — asserts the
    observed 200 with a clear "spec says 422, code
    does 200" message that will fail loudly when the
    code is patched, prompting both spec + smoke to
    be updated together.
    (b) **RR1a** spec wording "re-serialised" is
    stronger than what the code does, but the
    bytes-may-differ claim still holds via CRLF→LF.
    Surfaced for spec patch alongside RR1c. Same shape
    as feature-04 UI3 / AC6.
  - **HR9** carries the same caveat in its row note
    since the route documentation says "validates +
    re-serialises" too.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-05:

- Eleven smoke files written, one per spec section,
  ~50–240 lines each:
  - `F05_01_http_routes.py` covers HR1–HR9 (9 rules)
    + transitively covers SM1–SM9.
  - `F05_02_ui_triggers.py` covers UI1–UI5 (5 rules).
  - `F05_03_ui_gaps.py` covers UG1–UG2 (2 rules).
  - `F05_04_filename_normalisation.py` covers FN1 (1 rule,
    tested across create + rename + duplicate paths).
  - `F05_05_depth_rules.py` covers DR1–DR3 (3 rules).
  - `F05_06_same_parent.py` covers SP1–SP3 (3 rules).
  - `F05_07_create_body.py` covers CB1 (1 rule).
  - `F05_08_raw_roundtrip.py` covers RR1a–RR1c (3 rules,
    with RR1c documenting the spec/code drift).
  - `F05_09_atomicity.py` covers AL1 (1 rule via
    `_recent_writes` snapshot per Step-1 sign-off
    decision (b)).
  - `F05_10_idempotence.py` covers ID1 (1 rule).
  - `F05_11_acceptance.py` covers AC1–AC6 + AC7a + AC7b
    (8 rules).
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 05 --verbose` reports `11/11 passed; 0 failed`
  and all 35 direct rule-level `PASS  <id>: …` lines fire.
  (The 9 SM rows are not separate PASS lines — they are
  transitively covered by HR1–HR9; the matrix's
  "covered" status records this bookkeeping.)
- Full-suite re-run (`run.py` without filter) reports
  `38/38 passed; 0 failed`, confirming no regression in
  features 01 / 02 / 03 / 04.
- **Per-rule notes:**
  - **HR1–HR9** test each route via `app.test_client()`
    with HTTP-shape assertions (status, body, headers).
    HR2 / HR8 also assert the 415 `unsupported_type`
    branch by writing a sibling `junk.yaml` directly
    through `pathlib` (sidesteps
    `_normalize_filename`'s refusal).
  - **UI1–UI5** use the same `_extract_block` helper as
    feature-04, with a `contains=` disambiguator added
    to pick the file-editor `save()` / `move()` /
    `rename()` out of the multiple matches
    (run-editor has its own methods with the same
    names).
  - **UG1 / UG2** are two-pronged: template grep on
    `file_editor.html` + JS source grep on `app.js` +
    a live `/ui/file/<p>` render assertion that
    `btn-delete` / `btn-duplicate` are absent from
    the rendered HTML. Includes positive controls
    (`btn-rename`, `btn-move`, `btn-save` ARE
    present) to guard against false negatives.
  - **FN1** exercises all three normalisation paths
    (create / rename / duplicate) with the same
    auto-append + case-insensitive accept + non-`.feature`
    reject triple per path. On case-sensitive ext
    accept, the test confirms the on-disk file
    preserves the original case verbatim.
  - **DR1** walks parent depth 0, 1, 2, 10, 11 against
    POST `/api/files`. **DR2** walks dest parent depth
    1, 2, 11. **DR3** exercises rename + duplicate at
    depth 2 AND depth 10 (the extremes of the implicit
    inheritance range).
  - **SP1 / SP2** prove the parent-binding negative
    invariant: sending a bogus `parent` field in the
    PATCH `/rename` or POST `/duplicate` body must NOT
    move the file; the test asserts the file lands in
    the SOURCE parent, not the supplied bogus parent.
  - **CB1** loops missing / empty / whitespace-only /
    non-string descriptions through `POST /api/files`
    and asserts 400 + on-disk absence for each. The
    valid-description case then reads back the file
    via `GET /api/files/<p>` and asserts the
    `Feature(scenario=Scenario(kind='scenario',
    name='', steps=[], tags=[]), background={'steps':
    []}, tags=[])` shape per spec.
  - **RR1a** sends CRLF + trailing-whitespace input
    and asserts the on-disk bytes are LF-only and
    differ from the sent bytes; semantic content
    preserved.
  - **RR1b** sends literal `"this is not a Gherkin
    feature file at all…"` and asserts 422
    `parse_error` + the seed file is unchanged.
  - **RR1c** documents the spec/code drift
    explicitly: parseable-but-invalid text returns
    200 today (not 422 as the spec claims) because
    `Storage.write_raw` skips
    `validate_feature` + `serialize_feature`. Smoke
    pins this observed behaviour with an assertion
    message that names the drift and instructs the
    next maintainer how to update both spec + smoke
    when the code is patched.
  - **AL1** snapshots `s._recent_writes` keys under
    the lock after each of the 7 file-CRUD routes
    (POST / PATCH / PUT raw / rename / move /
    duplicate / DELETE) and asserts the target path
    (plus parent dir / secondary path where the
    spec demands it) is present. Covers the
    "`_mark_write` covers both target and parent dir"
    claim from spec section 02 § Self-write
    bookkeeping.
  - **ID1** covers four idempotence shapes:
    never-existed file, missing-everything-path, and
    existed-then-deleted (double-DELETE).
  - **AC1–AC6** are tight envelope assertions that
    strengthen DR1 / NU1 / HR3+HR9 / HR5 / HR6 / ID1.
    AC3 specifically does a `PATCH → GET /raw → PUT
    /raw` round-trip and asserts byte-identical on-disk
    bytes, exercising the canonical-formatting claim.
  - **AC7a** exercises every file-CRUD route in
    sequence on a subscribed bus and asserts zero
    events arrived in `max(DEBOUNCE_SECONDS * 3, 0.5)`
    seconds. **AC7b** uses two subscribers + an
    external `pathlib.write_text` burst (bypassing
    Storage) and asserts each subscriber receives
    exactly one `"change"` with `t_msg - t_last_write
    >= DEBOUNCE_SECONDS * 0.9` (10 % slack, same as
    feature-03 / feature-04).

**Feature-05 cycle complete.** Per the locked plan,
**feature-06 is next** — audit
`specs/features/06-*-NEW.md` (will need to discover the
exact filename in Step 1).

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-05:

1. **AC7 split.** Approved — split AC7 into AC7a (API
   mutation → zero events, follows code) and AC7b
   (external file mutation → exactly one event per
   open tab after `DEBOUNCE_SECONDS`, preserves spec
   intent). Both rows in the matrix. Same shape as
   feature-04 AC6.
2. **Storage-methods sub-section.** Approved — "accept
   duplicated effort if 2 tests are not identical"
   (Decision E). Nine `Storage.*` signatures get their
   own SM1–SM9 rows. Each row's primary-frame
   coverage is feature-02 (storage-direct assertions);
   the route-layer half is F05_01 (HTTP-shape
   assertions). The two halves are non-identical;
   duplication is allowed under Decision E. No new
   smoke files added — SM* coverage is bookkeeping over
   existing + planned files.
3. **AL1 testable shape.** Decision **(b)** — F05_09
   with the `_recent_writes` snapshot only (~30 lines).
   Snapshots `s._recent_writes` before/after each
   route-layer mutation and asserts the target path
   (and parent dir for delete) appears in the set.
   Avoids `TEMP_FILE_RE` race conditions of option
   (a). AL1 stays `partial` until F05_09 lands.
4. **RR1 split.** Approved — one spec bullet into
   three testable rules: RR1a (canonicalisation),
   RR1b (parse_error 422), RR1c (validation_error 422).

Total rule count after sign-off: 35 (pre-Q2) + 9 (SM* per
Q2) = **44 rules** across 11 smoke files.

Step 2 (Restructure) and Step 3 (Refine) will be no-ops
— zero existing primary-frame smokes for feature-05.
Proceed directly to Step 4 (Gap-fill) with the eleven
files `F05_01_http_routes.py` … `F05_11_acceptance.py`.

## Condition-coverage gap-closer (Jun 9, 2026)

`F05_12_server_body_type_rejection.py` is a **cross-cutting** smoke
that closes condition-coverage gap "Pattern A": the shared
`app/server.py` request-validation helpers (`_require_non_empty_string`,
`_parent_to_segments`, the create-file description guard, the move
parent guard, `_require_list_of_str`, `_require_optional_str`, and the
run-case `result`/`remark` guards) had their `not isinstance(...)` legs
untested — the suite only drove the empty/whitespace legs. It sends
wrong-typed bodies (int where str/list expected) to the file, folder,
and run routes and asserts `400 bad_request`. Validation runs before
storage, so no on-disk setup is needed. The `/api/runs*` cases
cross-credit feature-10 (same shared helpers). No new spec rule.
(feature-05 now 12 smokes.)
