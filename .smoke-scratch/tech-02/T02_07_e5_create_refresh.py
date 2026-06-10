# Pattern: see .smoke-scratch/README.md
"""tech-02 / E5 / create flows refresh their own sidebar tree.

specs/tech/02 § E5: the watcher suppresses `sse:change` for in-app self-writes,
so a newly-created artifact won't appear in its tree until an external change or
a manual Refresh. After a successful create, each flow re-GETs ONLY its own
tab's tree (decision D4): test case → #tree-pane, test run → #test-run-pane,
test report → #reports-pane. Static JS inspection.

Asserts:
1. tmsRefreshTreePane is defined and only re-GETs a mounted pane (guards on the
   pane's hx-get so an unmounted lazy pane is left to load fresh on first open).
2. tmsCreateFile  refreshes "tree-pane"      (Directory tree).
3. tmsCreateRun   refreshes "test-run-pane"  (Test-run tree).
4. tmsCreateReport refreshes "reports-pane"  (Reports tree).
"""
import pathlib
import re

STATIC = pathlib.Path("app/static")
sidebar = (STATIC / "02_sidebar.js").read_text(encoding="utf-8")


def body(text: str, pattern: str) -> str:
    m = re.search(pattern + r".*?\n\}", text, re.S)
    assert m, f"could not locate {pattern!r}"
    return m.group(0)


# 1. Helper exists, re-GETs only mounted panes (guards on hx-get).
fn = body(sidebar, r"function tmsRefreshTreePane\(paneId\)\s*\{")
assert 'getAttribute("hx-get")' in fn, (
    "tmsRefreshTreePane must read the pane's hx-get to detect a mounted pane"
)
assert re.search(r"if\s*\(\s*!url\s*\)\s*return", fn), (
    "tmsRefreshTreePane must skip unmounted panes (no hx-get → load fresh on open)"
)
assert 'htmx.ajax("GET", url,' in fn, "mounted pane must be re-GET via htmx.ajax"

# 2-4. Each create flow refreshes its own pane after success.
flows = {
    "03_folder_actions.js": ("tmsCreateFile", '"tree-pane"'),
    "04_run_create.js": ("tmsCreateRun", '"test-run-pane"'),
    "05_report_flows.js": ("tmsCreateReport", '"reports-pane"'),
}
for fname, (func, pane) in flows.items():
    src = (STATIC / fname).read_text(encoding="utf-8")
    assert f"tmsRefreshTreePane({pane})" in src, (
        f"{func} ({fname}) must call tmsRefreshTreePane({pane}) on successful create"
    )

print("PASS  T02_07: each create flow refreshes its own sidebar tree (case/run/report)")
