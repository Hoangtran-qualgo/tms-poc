# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-5 UI (top-bar button + tmsImportRun modal).

Render smoke: the "Import test run" button renders in the top bar beside
"Import test cases", wired to tmsImportRun().
JS source-inspection smoke (scoped to the tmsImportRun body): fetches
/api/run-groups (no "+ create group" row, IR-6), wires preview + commit via
raw fetch, renders the #/Scenario/Result/Matched-case preview, gates Confirm
on zero blocking errors, surfaces server reasons, gates file type + 30 MB,
clears the file input on success, and opens the new run by default.
"""
import pathlib
import re
import tempfile

from app import create_app

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(
    p.read_text() for p in sorted((REPO_ROOT / "app" / "static").glob("*.js"))
)


# --- U1: top bar renders the Import test run button -------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    shell = app.test_client().get("/").get_data(as_text=True)
    assert "tmsImportRun()" in shell, "U1: top bar missing Import test run wiring"
    assert "Import test run" in shell, "U1: top bar missing Import test run label"
    # Still beside the existing Import test cases button.
    assert "tmsImportFile()" in shell and "Import test cases" in shell, "U1: sibling button gone"
print("PASS  U1: top bar renders 'Import test run' beside 'Import test cases'")


# --- U2: tmsImportRun is defined (no-arg, top-bar launcher) -----------------
m = re.search(r"async function tmsImportRun\(\)\s*\{", JS)
assert m, "U2: tmsImportRun() must be defined as a no-argument top-bar launcher"
# Bound to just this function (up to the next top-level function) so negative
# assertions don't catch later concatenated files (05_..09_).
nxt = re.search(r"\n(?:async function|function) ", JS[m.end():])
body = JS[m.start(): m.end() + (nxt.start() if nxt else len(JS) - m.end())]
print("PASS  U2: tmsImportRun() controller is defined")


# --- U3: destination from /api/run-groups, no create-group row (IR-6) -------
assert '"/api/run-groups"' in body or "'/api/run-groups'" in body, "U3: must fetch /api/run-groups"
assert 'proj + "|" + grp' in body, "U3: 'Where' options must encode project|group"
assert "__new__" not in body, "U3 (IR-6): must NOT offer a '+ Create new group' row"
print("PASS  U3: destination picker from /api/run-groups, no create-group row")


# --- U4: wires preview + commit endpoints via RAW fetch (not tmsApiPost) ----
assert "/api/runs/import/preview" in body, "U4: must call the preview endpoint"
assert re.search(r'fetch\("/api/runs/import"', body), "U4: must call the commit endpoint via fetch"
assert "tmsApiPost(" not in body, "U4: must use raw fetch (not tmsApiPost) to keep details.reasons"
print("PASS  U4: preview + commit wired via raw fetch (preserves details.reasons)")


# --- U5: preview table columns # / Scenario / Result / Matched case ---------
for h in ("#", "Scenario", "Result", "Matched case"):
    assert ">" + h + "<" in body, f"U5: preview table missing the {h!r} column header"
print("PASS  U5: preview table renders #/Scenario/Result/Matched-case")


# --- U6: client gates file type + 30 MB -------------------------------------
assert 'accept=".html,.htm"' in body, "U6: file input must accept .html/.htm"
assert "30 * 1024 * 1024" in body, "U6: must enforce the 30 MB cap client-side"
assert r"/\.html?$/i" in body, "U6: must reject non-.html files client-side"
print("PASS  U6: client gates .html file type + 30 MB cap")


# --- U7: Confirm gates on zero blocking errors + surfaces server reasons ----
assert "blockingErrors.length" in body, "U7: Confirm must gate on zero blocking errors"
assert "setConfirmDisabled" in body, "U7: must gate the Confirm button"
assert "details.reasons" in body, "U7: must surface server import_validation_error reasons"
print("PASS  U7: Confirm gated on zero blocking errors; server reasons surfaced")


# --- U8: success clears the file input + opens the run by default -----------
assert 'fileInput.value = ""' in body, "U8: must clear the file input on success (report not retained)"
assert 'reportHtml = ""' in body, "U8: must clear the cached report html on success"
assert 'tmsRefreshTreePane("test-run-pane")' in body, "U8: must refresh the test-run pane on success"
assert '"/ui/run/"' in body and "htmx.ajax" in body, "U8: must open the new run in the main pane"
print("PASS  U8: success clears the report + opens the new run by default")
