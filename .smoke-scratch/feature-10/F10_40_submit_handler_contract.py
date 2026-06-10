"""Smoke 7f: submit handler contract.

Verifies that the rewritten `tmsCreateRun` submit path:
- POSTs `/api/runs/<project>/groups` only when the user picked the
  `+ Create new group...` row (conditional group creation);
- POSTs `/api/runs` with `case_paths: []` and `description: ""` (the
  Phase-3 case-picker is gone from the create flow per the rewrite);
- on success, navigates the main pane to the new run editor via
  `htmx.ajax('GET', '/ui/run/<...>.yaml', ...)`.
"""
import re, pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# 1. Conditional group POST guarded by the `isNew` branch.
m = re.search(
    r"if\s*\(\s*isNew\s*\)\s*\{[^}]*tmsApiPost\(\s*[`'\"][^`'\"]*?/api/runs/.*?/groups",
    APP_JS,
    re.S,
)
assert m, "expected POST /api/runs/<project>/groups inside `if (isNew)` branch"
print("PASS  group POST is conditional on the `+ Create new group...` branch")

# 2. POST /api/runs payload includes empty case_paths and empty description.
assert 'tmsApiPost("/api/runs"' in APP_JS, "missing POST /api/runs call site"
assert "case_paths: []" in APP_JS, "submit payload should send case_paths: []"
assert 'description: ""' in APP_JS, "submit payload should send description: ''"
print("PASS  run POST sends empty case_paths + empty description")

# 3. On success, navigate the main pane to the new run editor.
assert "htmx.ajax(" in APP_JS, "missing htmx.ajax navigation call"
assert (
    "/ui/run/${project}/${group}/${file_name}.yaml" in APP_JS
), "navigation URL must target /ui/run/<project>/<group>/<file_name>.yaml"
assert '"#main-pane"' in APP_JS, "navigation should swap into #main-pane"
print("PASS  success path opens the run editor via htmx.ajax → #main-pane")
