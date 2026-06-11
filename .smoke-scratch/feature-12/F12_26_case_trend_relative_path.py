# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / case_trend dropdown shows relative path.

The create-report modal already picks the project, so the `case_trend`
Test-case dropdown shows the project-relative path (rel_path) as the
option label while keeping the full path as the option value (the stored
case_path).

Static JS inspection of app/static/05_report_flows.js.
"""
import pathlib

JS = pathlib.Path("app/static/05_report_flows.js").read_text()

# The case_trend dropdown maps each feature to [full path, relative label].
assert "f.rel_path != null ? f.rel_path : f.path" in JS, (
    "case_trend option label must be the project-relative rel_path"
)
assert "features.map((f) => [f.path, f.rel_path" in JS, (
    "case_trend option VALUE must stay the full f.path"
)
# Guard against a regression to the old full-path-as-label mapping.
assert "features.map((f) => [f.path, f.path])" not in JS, (
    "case_trend still labels options with the full data-root path"
)
print("PASS  case_trend dropdown labels options with rel_path, value stays full path")
