# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- static asset / template wiring.

String-level asserts (per the F10_* convention) that the client-side
plumbing is present: the Reports sidebar tab + lazy pane, the new app.js
helpers, the RUN_RESULTS injection, and the detail's sse:change re-GET
plus the + Add runs hook.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2] / "app"
app_js = "\n".join(_p.read_text(encoding="utf-8") for _p in sorted((ROOT / "static").glob("*.js")))
base_html = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
detail_html = (ROOT / "templates" / "report_detail.html").read_text(encoding="utf-8")
sidebar_html = (ROOT / "templates" / "reports_sidebar.html").read_text(encoding="utf-8")

# app.js: the new helpers + activation wiring.
for needle in (
    "function tmsCreateReport(",
    "function tmsActivateReportsPane(",
    "function tmsBuildRunPicker(",
    "async function tmsAddReportRuns(",
    "async function tmsEditReportScope(",
    "/ui/reports-tree",
    'target === "reports"',
):
    assert needle in app_js, f"app.js missing: {needle}"

# base.html: third tab, lazy pane, RUN_RESULTS global.
assert 'data-sidebar-tab="reports"' in base_html, "missing Reports tab button"
assert 'id="reports-pane"' in base_html, "missing #reports-pane"
assert "window.TMS_RUN_RESULTS" in base_html, "missing RUN_RESULTS injection"

# report_detail.html: live re-GET on sse:change + Add runs hook.
assert 'hx-trigger="sse:change"' in detail_html, "detail must re-GET on sse:change"
assert "tmsAddReportRuns(" in detail_html, "detail must wire + Add runs"
assert "tmsEditReportScope(" in detail_html, "detail must wire Edit scope (tag_inventory)"

# reports_sidebar.html: create entry point.
assert "tmsCreateReport()" in sidebar_html, "sidebar must wire + New report"

print("PASS  F12_24: Reports tab/pane + app.js helpers + sse:change + Add-runs wiring present")
