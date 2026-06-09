# feature-01 · gherkin-io · coverage matrix

_Generated Jun 8, 2026 as Step 1 (Audit) of the smoke-suite
restructure plan in `IN-PROGRESS.md`._

## Method

- Spec source: `specs/features/01-feature-gherkin-io-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec (`raises`, `rejects`, `stores`,
  `filters`, `emits`, `returns`, …) + every bullet under
  the spec's `## Acceptance criteria` section.
- Bundled bullets split when sub-clauses are independently
  testable (e.g. tag-parser vs. cell-parser; the four
  cell-rendering rules).
- `Status` values: `covered` (existing smoke fails when the
  rule is violated), `partial` (rule is asserted only
  incidentally inside a smoke whose primary feature is
  not 01), `missing` (no smoke asserts the rule),
  `n/a` (rule is documentation-only / not testable).
  `partial` extends the locked `{covered, missing, n/a}`
  enum — pending user sign-off — to capture
  `F11_03`-style incidental round-trip coverage without
  overclaiming `covered`. (Approved Jun 8, 2026 at Step 2.)
- `Smoke file` column shows the file that owns the assertion.
  Per Decision A (locked Jun 8, 2026), feature-01 uses **one
  smoke per spec section** — five files total
  (`F01_01_parse_time.py` … `F01_05_acceptance.py`). All five
  exist as of Step 4 (Jun 8, 2026).

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| P1 | `\r\n` and lone `\r` normalised to `\n` before the source is handed to `gherkin-official`. | Invariants & rules → Parse-time | `F01_01_parse_time.py` | covered |
| P2 | A file without a `Feature:` header raises `GherkinParseError`. | Parse-time | `F01_01_parse_time.py` | covered |
| P3 | A file containing a `Rule:` block raises `GherkinParseError`. | Parse-time | `F01_01_parse_time.py` | covered |
| P4 | A file with more than one scenario raises `GherkinParseError`. | Parse-time | `F01_01_parse_time.py` | covered |
| P5 | A zero-scenario file is auto-fixed by injecting `Scenario(kind="scenario", name="", …)` so the next save persists it. | Parse-time | `F01_01_parse_time.py` | covered |
| P6 | `Feature.description` decoding: literal two-char `\n` sequences become real newlines; multi-line body description is concatenated into the same field. | Parse-time | `F01_01_parse_time.py` | covered |
| P7a | Tag parser strips the leading `@` character. | Parse-time | `F01_01_parse_time.py` | covered |
| P7b | Cell parser unescapes `\\` and `\|`. | Parse-time | `F01_01_parse_time.py` | covered |
| P8 | Non-canonical step keywords (e.g. non-English) are silently dropped. | Parse-time | `F01_01_parse_time.py` | covered |
| P9 | DocStrings, comments, blank lines, and `# language:` headers are parsed and discarded (enum directives are extracted before this discard — that exception is a feature-11 rule, see `F11_02`). | Parse-time | `F01_01_parse_time.py` | covered |
| V1 | `validate_feature` rejects an empty `Feature.description` (after `strip`). | Validate-time | `F01_02_validate_time.py` | covered |
| V2 | `validate_feature` rejects any tag (feature / scenario / examples) that fails `_is_valid_tag`: empty, contains whitespace, contains non-`0x21..0x7E` characters, contains `@`, or contains `,`. | Validate-time | `F01_02_validate_time.py` | covered |
| V3 | `validate_feature` rejects `Step.keyword` not in `CANONICAL_KEYWORDS = ("Given","When","Then","And","But")`. | Validate-time | `F01_02_validate_time.py` | covered |
| V4 | `validate_feature` rejects `Step.text` that is empty or contains a newline. | Validate-time | `F01_02_validate_time.py` | covered |
| V5 | `validate_feature` rejects `Scenario.name` containing a newline; empty is allowed. | Validate-time | `F01_02_validate_time.py` | covered |
| V6 | `validate_feature` rejects `kind == "outline"` with `len(examples) < 1`. | Validate-time | `F01_02_validate_time.py` | covered |
| V7 | `validate_feature` rejects `kind == "scenario"` with a non-empty `examples`. | Validate-time | `F01_02_validate_time.py` | covered |
| V8 | `validate_feature` rejects examples whose header is empty, and rejects any row whose length differs from the header. | Validate-time | `F01_02_validate_time.py` | covered |
| S1 | Serialiser de-dups tags per list (first occurrence wins, order preserved) and prepends each with `@`. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S2 | Serialiser encodes `Feature.description` real `\n` as the literal two-char `\n` so the `Feature:` line stays single-line. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S3a | Cell serialisation escapes `\\` before `\|` (order matters). | Serialize-time | `F01_03_serialize_time.py` | covered |
| S3b | Cell serialisation trims surrounding whitespace at write time. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S3c | Empty cells render as a single space. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S3d | Outline examples grid is column-aligned in the serialised output. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S4 | A `Background` with `steps == []` is omitted from the serialised output. | Serialize-time | `F01_03_serialize_time.py` | covered |
| S5 | Serialiser emits UTF-8 with LF line endings only. | Serialize-time | `F01_03_serialize_time.py` | covered |
| I1 | `serialize(parse(serialize(parse(x)))) == serialize(parse(x))` — second round-trip is byte-identical to the first. The first round-trip may canonicalise. | Idempotence target | `F01_04_idempotence.py` _(direct); `feature-11/F11_03_serialize_roundtrip.py` also exercises this incidentally_ | covered |
| AC1 | A hand-written `.feature` file with multi-line body description, CRLF line endings, and tags survives one round-trip with no semantic change (lossy fields aside). | Acceptance criteria | `F01_05_acceptance.py` | covered |
| AC2 | `serialize_feature(serialize_feature(x))` and `parse_feature(serialize_feature(parse_feature(serialize_feature(x))))` produce identical strings. | Acceptance criteria | `F01_05_acceptance.py` _(also transitive via I1)_ | covered |
| AC3 | `Rule:` / multi-scenario / no-`Feature:` files all raise `GherkinParseError` whose `line` attribute is **non-zero**. (Strengthens P2 / P3 / P4 with the `line > 0` claim.) | Acceptance criteria | `F01_05_acceptance.py` | covered |
| AC4 | Invalid tags raise `ValidationError` whose `field` attribute names the offending field. (Strengthens V2 with the `field`-name claim.) | Acceptance criteria | `F01_05_acceptance.py` | covered |

## Summary

- Total rules: **31** (9 parse-time, 8 validate-time, 8 serialize-time, 1 idempotence, 4 acceptance, accounting for the splits noted under Method).
- `covered`: **31**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-01 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 01`
exits zero with all five smokes green).

## Notes & flags

- **Zero direct coverage at audit time (Jun 8, 2026, Step 1).**
  No smoke targeted feature-01 in its primary frame. The
  closest neighbours were `feature-11/F11_02_parser_directives.py`
  and `feature-11/F11_03_serialize_roundtrip.py` (primary feature 11),
  which incidentally exercised comment discard (P9) and
  round-trip stability (I1) for enum-bearing features only.
  Per the locked cross-feature rule, those smokes stayed in
  their primary feature; Step 4 added the five
  feature-01-primary smokes that now cover all 31 rules
  directly.
- **AC ↔ rule overlap.** AC1 / AC2 / AC3 / AC4 partially
  restate P-/V-/S-/I- rules with a slightly stronger
  assertion (CRLF survival, byte-identical double serialize,
  `line > 0` in the error envelope, `field`-named in the
  error envelope). They are kept as separate rows because
  the additional claim is independently testable; a single
  smoke can cover an underlying rule + its AC restatement
  together when convenient.
- **No `n/a` rows.** Every rule in the spec is testable in
  pure-module form (no FS, no HTTP, no Flask required).
- **Step-2 granularity decision (resolved Jun 8, 2026):**
  one file per spec section (Decision A). Five files planned
  for feature-01: `F01_01_parse_time.py` (P1–P9),
  `F01_02_validate_time.py` (V1–V8),
  `F01_03_serialize_time.py` (S1–S5 inc. S3a–d),
  `F01_04_idempotence.py` (I1),
  `F01_05_acceptance.py` (AC1–AC4).

## Step 2 execution log

**Jun 8, 2026** — Step 2 (Restructure) executed for feature-01:

- Step-1 sign-off received (31-row matrix accepted; `partial`
  status accepted; I1 / AC2 `partial` marking accepted).
- Decision A (one file per spec section) and Decision (i)
  (global setup files land in feature-01's Step 2) selected.
- `git mv` was a no-op: feature-01 had zero existing smokes
  to move (audit finding confirmed during Step 2). The
  five `F01_*.py` files remain `(planned)` until Step 4.
- Global prerequisites created: `.smoke-scratch/README.md`
  (canonical boilerplate pattern + filename convention +
  runner usage) and `.smoke-scratch/run.py` (~90-line
  walker with `--filter`, `--list`, `--verbose`).

Next step: **Step 3 (Refine)** is a no-op for feature-01
(no existing smokes to refine). Cycle proceeds directly to
Step 4.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-01:

- Five smoke files written, one per spec section, ~30 – 130
  lines each:
  - `F01_01_parse_time.py` covers P1–P9 (9 rules).
  - `F01_02_validate_time.py` covers V1–V8 (8 rules).
  - `F01_03_serialize_time.py` covers S1, S2, S3a–d, S4, S5
    (8 rules).
  - `F01_04_idempotence.py` covers I1 (1 rule).
  - `F01_05_acceptance.py` covers AC1–AC4 (4 rules).
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- F01_02 and F01_03 use small within-file helpers (`_good()`,
  `_expect()`, `_feat()`) per the locked plan: helpers are
  permitted *within* a single smoke file, not across files.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 01 --verbose` reports `5/5 passed; 0 failed`
  and all 31 rule-level `PASS  <id>: …` lines fire.
- I1 and AC2 status promoted from `partial` to `covered`:
  feature-01 now owns its own direct round-trip and
  fixed-point smokes; `F11_03` retains incidental coverage
  but is no longer the only assertion.

**Feature-01 cycle complete.** Per the locked plan,
**feature-02 is next** — audit `specs/features/02-feature-storage-core-NEW.md`.

_Correction (Jun 8, 2026, after feature-02 Step 1):_ an
earlier draft of this paragraph said feature-02's Step 2
would `git mv` "7 `p2_*.py` smokes". Both numbers are
wrong: there are 13 `p2_*` files, and **none** of them
are feature-02 primary. The `p2_` prefix denotes the
test-run feature's **Phase 2** (primary feature 10), not
feature-02. Feature-02's Step 2 is a no-op `git mv`, same
shape as feature-01's. Same applies to features 03 – 09.

## Condition-coverage gap-closer (Jun 9, 2026)

`F01_06_tag_non_ascii.py` hardens the tag char-range check in
`models._is_valid_tag` (`if cp < 0x21 or cp > 0x7E`). The prior suite
drove only the `cp < 0x21` leg (space/control) and the `@`/`,`
exclusions; this smoke drives the previously-untested **`cp > 0x7E`
leg** (non-ASCII char, e.g. `café`) both at the unit predicate and
through the public `validate_feature` rejection (`scenario.tags[0]`).
No new spec rule — it closes a condition-coverage gap on V-rule tag
validation. (feature-01 now 6 smokes.)
