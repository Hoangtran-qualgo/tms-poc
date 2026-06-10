# `.smoke-scratch/` — standalone smoke suite

Each file under `feature-<N>/` is one self-contained Python script
that exercises a slice of the spec at `specs/features/<N>-*.md`.
There is **no test harness** (no `pytest`, no fixtures, no
conftest). Each smoke is its own entry point, runnable with one
shell command, and fails by raising `AssertionError` from the
exact line the spec was violated.

## Pattern

Every smoke follows the same skeleton:

```python
# Pattern: see .smoke-scratch/README.md
import pathlib, tempfile
from app import create_app

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    # ... arrange, act, assert ...
    assert <invariant>, "<rule the assertion enforces>"
    print("PASS  <one-line description of what was checked>")
```

Variations:

- **Pure-model smokes** (e.g. parser / serializer / validator
  for feature-01) can skip the `create_app` step and import
  from `app.gherkin_io` / `app.models` directly.
- **HTTP smokes** use `app.test_client()` after the `create_app`
  call instead of touching `storage` directly.
- **JS / template smokes** use `app.test_client().get(...)`
  and inspect the rendered HTML with the `re` module — no
  browser, no Playwright.
- **JS *source*-inspection smokes** read the client JS as text and
  regex for function bodies / wiring. `app/static/app.js` was split
  into ordered `NN_*.js` files (specs/tech/01-tech-restructure-NEW.md),
  so these read the **concatenation** of all of them, which
  reconstructs the original single-file source view:

  ```python
  JS = "\n".join(
      _p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js"))
  )
  ```

  `sorted()` over the `NN_` prefix yields the same order the files
  load in `base.html` (= the original source order), so a regex that
  grabs the *first* match of a method shared by two controllers
  (e.g. `boot()` on the run editor vs. the file editor) still resolves
  to the right one. Concatenating (rather than reading one specific
  file) keeps a smoke correct when a symbol is moved between split
  files, and lets smokes that span areas (tree + bootstrap listener,
  run editor + sse fan-out) assert in one pass. Per *No shared
  helpers* below, this line is copy-pasted, not factored out.

## Filename convention

```
.smoke-scratch/feature-<N>/F<N>_<MM>_<spec-section-slug>.py
```

- `<N>` is the spec feature number from `specs/features/<N>-*.md`
  (zero-padded to 2 digits).
- `<MM>` is zero-padded, restarts at `01` per directory, and
  is assigned in spec-section order. New smokes append at the
  end; existing files are **never renumbered** (would break
  cross-file references in comments).
- `<spec-section-slug>` is the snake_case version of the spec
  section the smoke covers (e.g. `parse_time`, `validate_time`,
  `serialize_time`, `idempotence`, `acceptance`). Decision A
  (locked Jun 8, 2026): one file per section, each densely
  asserting all rules in that section.

## Running

One file:

```sh
PYTHONPATH=. .venv/bin/python .smoke-scratch/feature-01/F01_01_parse_time.py
```

All files:

```sh
.venv/bin/python .smoke-scratch/run.py
```

One feature:

```sh
.venv/bin/python .smoke-scratch/run.py --filter 01
```

Listing without running:

```sh
.venv/bin/python .smoke-scratch/run.py --list
```

Verbose (echo each smoke's `PASS …` lines):

```sh
.venv/bin/python .smoke-scratch/run.py --verbose
```

Exit code: `0` if every smoke passes, `1` if any fails.

## Coverage tracking

Each `feature-<N>/` directory ships a `COVERAGE.md` mapping every
spec rule to the smoke file that asserts it. Status values:

- `covered` — at least one smoke fails when this rule is violated.
- `partial` — the rule is asserted only incidentally inside a
  smoke whose primary feature is some other `<N>`.
- `missing` — no smoke asserts this rule.
- `n/a` — rule is documentation-only / not testable.

"Done" for a feature means every rule in its `COVERAGE.md` is
`covered` (no `missing` rows) and `run.py --filter <N>` is green.

## Conventions

- **One `PASS  …` print per assertion bundle.** The string after
  `PASS` should name the rule, not the implementation detail.
- **Assertion messages are mandatory.** Every `assert` carries
  a message that pinpoints which spec rule was violated.
- **No shared helpers.** Copy-paste the boilerplate. The
  one-file-is-the-whole-test property is the goal; coupling
  smokes through a shared module breaks it.
- **No network, no real filesystem outside `tempfile`.** Every
  smoke creates a `TemporaryDirectory` and cleans up via the
  `with` block.
