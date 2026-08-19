# Pattern: see .smoke-scratch/README.md
"""feature-17 / multi-file import / modal source-inspection smoke."""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(
    path.read_text() for path in sorted((REPO_ROOT / "app" / "static").glob("*.js"))
)


match = re.search(r"async function tmsImportFile\(\)\s*\{", JS)
assert match, "U1: tmsImportFile() controller is missing"
body = JS[match.start():]

# --- U1: picker accepts multiple files and gates both client limits ----------
assert 'accept=".feature" multiple' in body, "U1: picker must allow multiple .feature files"
assert "files.length > 20" in body, "U1: client must reject a batch over 20 files"
assert "totalBytes > 3 * 1024 * 1024" in body, "U1: client must reject a batch over 3 MB total"
assert "Array.from(fileInput.files || [])" in body, "U1: controller must read the full FileList"
assert "Promise.allSettled" in body, "U1: file reads must collect per-file failures"
print("PASS  U1: modal selects all files and enforces the 20-file / 3 MB limits")


# --- U2: preview/commit send sources, show source context, and gate errors --
assert 'body: JSON.stringify({ sources: sourceItems })' in body, (
    "U2: preview must submit ordered source entries"
)
assert "sources: sourceItems," in body, "U2: commit must submit ordered source entries"
assert ">Source file<" in body, "U2: preview table must show source-file context"
assert "previewErrors = data.errors || []" in body, "U2: preview errors must be retained"
assert "previewErrors.length === 0" in body, "U2: preview errors must disable Import"
assert "Fix every source before importing:" in body, "U2: errors must be shown together"
print("PASS  U2: modal previews source context and blocks commit on any source error")


# --- U3: one acknowledgement identifies every enum-bearing source -----------
assert "enumSources = data.enum_sources || []" in body, "U3: enum source context is missing"
assert "source.source_name" in body, "U3: enum acknowledgement must name affected sources"
assert "enumAck.checked" in body, "U3: one enum acknowledgement must gate Import"
print("PASS  U3: one enum acknowledgement covers and identifies affected sources")
