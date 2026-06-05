"""3.B partial — Wiring smoke for the + New run flow.

End-to-end click behaviour needs a browser (per Phase-2 lock-in: manual
verification for client interactions). This smoke verifies every static
artefact the flow depends on:

- folder_test_run_group.html's toolbar + empty-state buttons call
  tmsCreateRun(<project>, <group>) with the right args.
- app.js exposes tmsCreateRun, tmsBuildCasePicker,
  tmsFetchProjectFeaturePaths, tmsSlugifyForFilename.
- tmsOpenModal accepts the new size parameter ('lg' for the picker).
- The modal posts to /api/runs and navigates to /ui/run/<...>.yaml on
  success.
"""
import re
import pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()
GROUP_TPL = pathlib.Path("app/templates/folder_test_run_group.html").read_text()

# --- 1. Template wires both entry points to tmsCreateRun(...) ----------
toolbar_re = re.compile(r"tmsCreateRun\('\{\{ ?project ?\}\}', ?'\{\{ ?group ?\}\}'\)")
assert toolbar_re.search(GROUP_TPL), "toolbar button missing tmsCreateRun wiring"
# Both the toolbar and the empty-state CTA reference tmsCreateRun.
count = len(toolbar_re.findall(GROUP_TPL))
assert count == 2, f"expected 2 tmsCreateRun call sites in template, got {count}"
print("PASS 3.B group template wires + New run + empty-state CTA")

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
