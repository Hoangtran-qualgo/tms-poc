"""3.B partial — Wiring smoke for the + New run flow.

End-to-end click behaviour needs a browser (per Phase-2 lock-in: manual
verification for client interactions). This smoke verifies static
artefacts the flow depends on.

Updated for the "Relocate + simplify the + New run flow" change: the
button moved from `folder_test_run_group.html` to `test_run_sidebar.html`
(template-side assertion inverted; tighter coverage of the new wiring
lives in F10_35..F10_40). The JS-side assertions below remain valid: the
four exported symbols are still defined, the modal-size param still
ships (the `lg` width now belongs to the run editor's `+ Add test case`
picker rather than `tmsCreateRun`), and the rewritten `tmsCreateRun`
keeps the same POST + navigation contract.
"""
import re
import pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))
GROUP_TPL = pathlib.Path("app/templates/folder_test_run_group.html").read_text()

# --- 1. Template no longer hosts tmsCreateRun (moved to sidebar) -------
# Use a call-site regex so prose mentions inside Jinja `{# ... #}` comments
# (e.g. an explanatory pointer to the sidebar) don't trip the assertion.
call_site_re = re.compile(r"\btmsCreateRun\s*\(")
assert not call_site_re.search(GROUP_TPL), (
    "tmsCreateRun() call site should no longer be wired in the group view "
    "template; it now lives in test_run_sidebar.html "
    "(covered by F10_23 / F10_24)."
)
print("PASS 3.B group template no longer hosts run-creation affordance")

# --- 2. New JS symbols defined -----------------------------------------
for sym in [
    "function tmsCreateRun(",
    "function tmsBuildCasePicker(",
    "function tmsFetchProjectFeaturePaths(",
    "function tmsSlugifyForFilename(",
]:
    assert sym in APP_JS, f"missing JS symbol: {sym}"
print("PASS 3.B all new JS symbols defined")

# --- 3. tmsOpenModal accepts size and tmsCreateRun uses size: 'lg' -----
assert "size = \"md\"" in APP_JS, "tmsOpenModal should default size to md"
assert "max-w-2xl" in APP_JS and "max-w-md" in APP_JS, "size class mapping missing"
assert re.search(r"size:\s*\"lg\"", APP_JS), "tmsCreateRun should request size: 'lg'"
print("PASS 3.B modal size param wired")

# --- 4. POST /api/runs + navigation contract --------------------------
assert 'tmsApiPost("/api/runs"' in APP_JS, "POST endpoint wrong"
assert (
    '/ui/run/${project}/${group}/${file_name}.yaml' in APP_JS
), "navigation URL wrong"
print("PASS 3.B POST /api/runs + /ui/run/... navigation wired")
