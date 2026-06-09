# 01 · Gherkin I/O

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/gherkin_io.py`, `app/models.py`, `app/errors.py`._

## Summary

Pure text ↔ model layer for `.feature` files. The rest of the
application is forbidden from importing `gherkin-official` directly;
all parsing and serialisation goes through this module. Round-trip
idempotence is the headline invariant — once a file has been written
by the serializer, parsing and re-serialising must produce byte-for-
byte identical output.

## Scope

In scope:

- Parsing a `.feature` source string into a `Feature` dataclass.
- Validating a `Feature` against the write-time invariants.
- Serialising a validated `Feature` back to canonical source text.
- Defining the dataclass model (`Feature`, `Background`, `Scenario`,
  `Step`, `ExamplesTable`) and its JSON wire shape (`to_dict` /
  `from_dict`).
- Wrapping `gherkin-official` parser exceptions in a domain error
  type (`GherkinParseError`) carrying line / column / message.

Out of scope:

- File I/O (lives in `storage-core`).
- HTTP transport (lives in `testcase-crud` and `file-editor`).
- Multi-feature / multi-scenario files (rejected at parse).
- `Rule:` blocks (rejected at parse).

## Public surface

Functions exported from `app.gherkin_io`:

- `parse_feature(source: str) -> Feature`
- `serialize_feature(feature: Feature) -> str`
- `_normalize_newlines(source: str) -> str` (module-private;
  mentioned because the EOL normalisation rule is part of the
  contract).

Dataclasses exported from `app.models`:

- `Feature(description, tags, background, scenario)`
- `Background(steps)`
- `Scenario(kind, name, tags, steps, examples)`
- `Step(keyword, text, data_table)`
- `ExamplesTable(tags, name, header, rows)`
- Constants: `CANONICAL_KEYWORDS = ("Given","When","Then","And","But")`,
  `SCENARIO_KINDS = ("scenario","outline")`.
- Function: `validate_feature(feature) -> None` (raises
  `ValidationError`).

Errors raised:

- `GherkinParseError(line, column, message)` — HTTP 422.
- `ValidationError(field, message)` — HTTP 422.

## Invariants & rules

**Parse-time**

- Normalise EOLs: `\r\n` and lone `\r` → `\n` before handing source
  to `gherkin-official`.
- Reject files without a `Feature:` header (`GherkinParseError`).
- Reject `Rule:` blocks.
- Reject files with more than one scenario.
- Auto-fix zero-scenario files by injecting
  `Scenario(kind="scenario", name="", …)`. Next save persists it.
- `Feature.description` decoded: literal two-char `\n` sequences →
  real newlines; multi-line body description block concatenated
  into the same field.
- Tag parser strips a leading `@`; cell parser unescapes `\\` and
  `\|`.
- Non-canonical step keywords (e.g. non-English) silently dropped.
  Documented data-loss risk.
- DocStrings, comments, blank lines, and `# language:` headers
  parsed and discarded.

**Validate-time (`validate_feature`)**

- `Feature.description` non-empty after strip.
- Every tag (feature, scenario, examples) passes `_is_valid_tag`:
  non-empty, no whitespace, ASCII printable
  (`0x21..0x7E`), excludes `@` and `,`.
- `Step.keyword` ∈ `CANONICAL_KEYWORDS`.
- `Step.text` single-line and non-empty.
- `Scenario.name` single-line (may be empty).
- `kind == "outline"` → `len(examples) >= 1`.
- `kind == "scenario"` → `examples == []`.
- Examples header non-empty, every row length matches header.

**Serialize-time**

- Tags de-duped per list (first occurrence wins, order preserved),
  prepended with `@`.
- `Feature.description` real `\n` → literal two-char `\n` on disk
  (so the `Feature:` line stays single-line).
- Cells: `\\` first, then `\|`. Whitespace trimmed at write.
  Empty cells render as a single space. Output column-aligned.
- Background omitted from disk when `background.steps == []`.
- UTF-8 + LF line endings only.

**Idempotence target**

`serialize(parse(serialize(parse(x)))) == serialize(parse(x))`. The
first round-trip may canonicalise.

## Affects

- `02-storage-core`: every read / write path calls
  `parse_feature` / `serialize_feature`. Storage owns the bytes;
  this module owns the meaning.
- `05-testcase-crud`: `POST /api/files` constructs the placeholder
  scenario via the model dataclasses defined here.
- `08-file-editor`: structured tab consumes the canonical JSON wire
  shape (`Feature.to_dict`); raw tab triggers `parse_feature` on
  `PUT …/raw` server-side.
- `09-search`: enumerates parsed `Feature` objects; never re-parses.

## Depends on

- `gherkin-official >=32,<33` (parser only — the project never
  consumes its emit/format helpers).
- Python `>=3.12` for `slots=True` dataclasses.
- No filesystem, no network, no Flask. Pure module — keeps it
  testable and import-cheap.

## Surface for follow-up

- Adding any new on-disk syntax (e.g. comments, doc-strings, custom
  keyword languages) requires changes here first, with the
  data-loss caveats updated in `business-rule.md`.
- The dataclass model is the single canonical shape; any new
  on-disk attribute should extend `to_dict` / `from_dict` here,
  then flow outward. (`10-feature-test-run` references cases by
  external `file_path` instead of extending this dataclass, but a
  future "result history per case" view would likely add such a
  field.)
- Migrating away from `gherkin-official` would be a contained
  change because no other module imports it.

## Acceptance criteria

- A hand-written `.feature` file with multi-line body description,
  CRLF line endings, and tags survives one round-trip with no
  semantic change (lossy fields aside).
- `serialize_feature(serialize_feature(x))` and `parse_feature(
  serialize_feature(parse_feature(serialize_feature(x))))` produce
  identical strings.
- `Rule:` block, multi-scenario, and no-`Feature:` files all raise
  `GherkinParseError` with a non-zero line number.
- Invalid tags (containing whitespace, `@`, or `,`) raise
  `ValidationError` with the offending field name.
