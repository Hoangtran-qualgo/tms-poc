# Pattern: see .smoke-scratch/README.md
"""feature-14 / import test cases / Phase 4 UI (Import button + modal).

Render smoke: the Import button appears beside "+ Create test case" in both
the module and sub-folder views, wired to tmsImportFile(<folder>).
JS source-inspection smoke: tmsImportFile exists and wires the preview +
commit endpoints, the per-scenario filename inputs, the enum-drop
acknowledgement gate, and the success refresh of folder + tree.
"""
import pathlib
import re
import tempfile

from app import create_app

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(
    p.read_text() for p in sorted((REPO_ROOT / "app" / "static").glob("*.js"))
)


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = app.extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_folder(["proj", "mod", "sub"])
    c = app.test_client()

    # --- U1: global top bar renders the Import button (no arg) --------------
    shell = c.get("/").get_data(as_text=True)
    assert "tmsImportFile()" in shell, "U1: top bar missing Import button wiring"
    assert "Import test cases" in shell, "U1: top bar missing Import button label"
    print("PASS  U1: global top bar renders the Import test cases button")

    # --- U2: Import button moved OUT of the folder views --------------------
    mod_html = c.get("/ui/folder/proj/mod").get_data(as_text=True)
    sub_html = c.get("/ui/folder/proj/mod/sub").get_data(as_text=True)
    assert "tmsImportFile" not in mod_html, "U2: module view must no longer carry the Import button"
    assert "tmsImportFile" not in sub_html, "U2: sub-folder view must no longer carry the Import button"
    assert "tmsCreateFile('proj/mod')" in mod_html, "U2: create button must still be present"
    print("PASS  U2: Import button removed from folder views (now top-bar only)")


# --- U3: tmsImportFile is defined --------------------------------------------
m = re.search(r"async function tmsImportFile\(parent\)\s*\{", JS)
assert m, "U3: tmsImportFile(parent) must be defined"
body = JS[m.start():]
print("PASS  U3: tmsImportFile(parent) controller is defined")


# --- U4: builds destination picker from /api/tree (relative display) ---------
assert '"/api/tree"' in body or "'/api/tree'" in body, "U4: must fetch /api/tree for folder picker"
assert "foldersByProject" in body, "U4: must build per-project destination folder list"
assert "f.slice(prefix.length)" in body, (
    "U4: destination folders must display relative to the chosen project"
)
print("PASS  U4: project + destination picker from /api/tree, folders shown relative to project")


# --- U5: wires preview + commit endpoints ------------------------------------
assert "/api/files/import/preview" in body, "U5: must call the preview endpoint"
assert "/api/files/import" in body, "U5: must call the commit endpoint"
print("PASS  U5: wires preview (dry-run) and commit endpoints")


# --- U6: per-scenario preview table + placeholder-only filename inputs -------
for h in ("Scenario name", "Feature tag", "Scenario tag", "File name"):
    assert ">" + h + "<" in body, f"U6: preview table missing the {h!r} column header"
assert 'data-role="filename"' in body, "U6: must render per-scenario filename inputs"
assert 'input.placeholder = "file name"' in body, "U6: filename input must use the 'file name' placeholder"
assert "input.value = tmsSlugifyForFilename" not in body, "U6: filename inputs must NOT be pre-filled"
assert "full.slice(0, 30)" in body, "U6: scenario name must be truncated to 30 chars with an ellipsis"
assert "+ more" in body and "t.slice(0, 2)" in body, "U6: tags must show top 2 + N-more, @-prefixed"
assert 'size: "xl"' in body, "U6: modal must use the wider 'xl' size"
print("PASS  U6: bordered preview table (name/feature-tag/scenario-tag/file) with placeholder filenames, wide modal")


# --- U7: client-side file-type + size gating + styled picker -----------------
assert ".feature" in body, "U7: must reject non-.feature files client-side"
assert "3 * 1024 * 1024" in body, "U7: must enforce the 3 MB cap client-side"
assert "file:border-2" in body, "U7: Choose-file button must have an outstanding border style"
print("PASS  U7: client gates file type + 3 MB and the file picker is visually styled")


# --- U8: enum-drop acknowledgement gates Confirm -----------------------------
assert 'data-role="enum-ack"' in body, "U8: must render an enum-drop acknowledgement"
assert "enumsPresent" in body and "enumAck.checked" in body, "U8: Confirm must gate on enum ack"
assert "setConfirmDisabled" in body, "U8: must gate the Confirm button"
print("PASS  U8: enum-drop acknowledgement + filename completeness gate Confirm")


# --- U9: success refreshes the destination folder + tree ---------------------
assert "tmsRefreshFolder(parentPath)" in body, "U9: must refresh the destination folder on success"
assert 'tmsRefreshTreePane("tree-pane")' in body, "U9: must refresh the tree pane on success"
print("PASS  U9: success refreshes the destination folder and tree panes")


# --- U10: import-validation reasons surfaced ---------------------------------
assert "reasons" in body, "U10: must surface server import_validation_error reasons"
print("PASS  U10: server validation reasons are surfaced to the user")
