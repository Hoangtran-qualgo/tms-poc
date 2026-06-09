# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP5 -- raw tab scaffold.

Render-and-grep that #tab-raw contains:
  - <textarea id='raw-text'> (the editable buffer)
  - #raw-error error-display region (initially hidden)
  - #btn-save-raw button (visible label 'Save raw')
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    html = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)


# Isolate the raw tab container so assertions can't be satisfied by the
# structured tab's elements.
m = re.search(r'<div[^>]*id="tab-raw"[\s\S]*?</div>\s*</div>', html)
assert m, "TP5: rendered editor must include <div id='tab-raw'> container"
raw_block = m.group(0)

assert re.search(
    r'<textarea[^>]*id="raw-text"', raw_block
), "TP5: raw tab must include <textarea id='raw-text'>"

# #raw-error: hidden by default, lives inside the raw tab.
m_err = re.search(
    r'<div[^>]*id="raw-error"[^>]*class="([^"]*)"', raw_block
)
assert m_err, "TP5: raw tab must include <div id='raw-error'>"
assert "hidden" in m_err.group(1), (
    f"TP5: #raw-error must carry the `hidden` class initially; "
    f"got class={m_err.group(1)!r}"
)

# Save-raw button.
m_btn = re.search(
    r'<button[^>]*id="btn-save-raw"[^>]*>([\s\S]*?)</button>', raw_block
)
assert m_btn, "TP5: raw tab must include <button id='btn-save-raw'>"
label = re.sub(r"&[a-z]+;", "", m_btn.group(1)).strip()
assert label == "Save raw", (
    f"TP5: #btn-save-raw label must be 'Save raw'; got {label!r}"
)

print("PASS  TP5: raw tab renders #raw-text textarea, hidden #raw-error region, #btn-save-raw button")
