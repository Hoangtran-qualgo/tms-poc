# Pattern: see .smoke-scratch/README.md
"""feature-16 / tree template count labels."""
from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app


SOURCE = """Feature: Mixed

@Auto
Scenario: Automated
  Given automated

Scenario: Manual
  Given manual
"""


with TemporaryDirectory() as td:
    root = Path(td)
    branch = root / "project" / "module" / "branch"
    branch.mkdir(parents=True)
    (branch / "case.feature").write_text(SOURCE, encoding="utf-8")
    app = create_app(data_root=root)
    try:
        html = app.test_client().get("/ui/tree").get_data(as_text=True)
    finally:
        app.extensions["watcher"].stop()

assert "module (2-1-1)" in html, (
    "TM1: module folder name must show total-auto-non_auto scenario counts"
)
assert "branch (2-1-1)" in html, (
    "TM2: nested branch folder name must show recursive scenario counts"
)
assert "project (2-1-1)" in html, (
    "TM3: project folder name must show recursive scenario counts"
)
assert 'data-path="project/module"' in html, (
    "TM4: count label must preserve module folder navigation row"
)
assert 'hx-get="/ui/folder/project/module"' in html, (
    "TM5: count label must preserve module HTMX navigation"
)

print("PASS  TM1-TM5: tree renders project/module/branch counts and preserves navigation")
