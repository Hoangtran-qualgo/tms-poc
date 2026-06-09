# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / SR1 + SR2 + SR3 -- raw save flow.

SR1: saveRaw() calls hideRawError() then PUT /api/files/<p>/raw with
     state.raw as text/plain.
SR2: 422 parse_error -> showRawError formats "Line N, col M: <msg>"
     when details.line is present; plain message otherwise. End-to-end
     PUT confirms the server-side envelope shape.
SR3: 2xx -> await _refreshFromDisk() then flashSaved().

Cross-credit (SR1): feature-05/F05_02_ui_triggers.py UI5 owns the
endpoint+verb+body assertions; this smoke owns the hideRawError +
flow ordering claims.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


# --- Locate saveRaw() body. ---
m = re.search(r"async\s+saveRaw\s*\(\s*\)\s*\{", JS)
assert m, "SR-suite: tmsEditor.saveRaw() must exist"
start = m.end() - 1
depth = 0
for i in range(start, len(JS)):
    c = JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            BODY = JS[start:i + 1]
            break


# --- SR1: hideRawError() then PUT /raw with text/plain + state.raw. ---
# hideRawError must be the FIRST statement (or close to it) before the fetch.
hide_idx = BODY.index("this.hideRawError()")
put_idx = BODY.index('fetch("/api/files/')
assert hide_idx < put_idx, (
    "SR1: saveRaw must call hideRawError() BEFORE the PUT fetch"
)
assert re.search(
    r'method:\s*"PUT"', BODY
), "SR1: saveRaw must issue PUT"
assert re.search(
    r'"Content-Type":\s*"text/plain"', BODY
), "SR1: saveRaw must declare Content-Type: text/plain"
assert "body: this.state.raw" in BODY, (
    "SR1: saveRaw body must be this.state.raw"
)
assert re.search(
    r'fetch\(\s*"/api/files/"\s*\+\s*this\.state\.path\s*\+\s*"/raw"', BODY
), "SR1: saveRaw must target /api/files/<state.path>/raw"


# --- SR2: 422 branch + showRawError formatting. ---
# saveRaw catches the non-ok branch, reads j.error.details.line/column.
assert re.search(
    r'const\s+loc\s*=\s*j\?\.\s*error\?\.\s*details', BODY
), "SR2: saveRaw must read details from the error envelope"
assert re.search(
    r'loc\s*&&\s*loc\.line', BODY
), "SR2: saveRaw must branch on loc.line truthiness"
# Format includes both literal markers.
assert re.search(
    r'`Line\s+\$\{loc\.line\}\s*,\s*col\s+\$\{loc\.column\}:\s*\$\{msg\}`',
    BODY,
), "SR2: parse-error message format must be 'Line N, col M: <msg>' template literal"
# showRawError body sets textContent + un-hides #raw-error.
SR = re.search(r"showRawError\s*\(\s*msg\s*\)\s*\{([\s\S]+?)\n\s{0,4}\}", JS)
assert SR, "SR2: tmsEditor.showRawError(msg) must exist"
sr_body = SR.group(1)
assert 'getElementById("raw-error")' in sr_body, (
    "SR2: showRawError must target #raw-error"
)
assert "el.textContent = msg" in sr_body, (
    "SR2: showRawError must set #raw-error textContent to the message"
)
assert 'el.classList.remove("hidden")' in sr_body, (
    "SR2: showRawError must un-hide #raw-error"
)

# End-to-end: malformed PUT actually returns a 422 envelope with details.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    r = client.put(
        "/api/files/Alpha/Mod/case.feature/raw",
        data=b"not valid gherkin at all\n",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 422, (
        f"SR2 end-to-end: malformed Gherkin PUT must return 422, got {r.status_code}"
    )
    env = r.get_json()
    assert env["error"]["code"] == "parse_error", (
        f"SR2 end-to-end: envelope code must be 'parse_error'; "
        f"got {env['error']['code']!r}"
    )
    details = env["error"].get("details", {})
    assert "line" in details and "column" in details, (
        f"SR2 end-to-end: parse_error details must carry line + column; "
        f"got {details!r}"
    )


# --- SR3: 2xx -> await _refreshFromDisk() then flashSaved(). ---
assert re.search(
    r'await\s+this\._refreshFromDisk\(\s*\)\s*;\s*this\.flashSaved\(\s*\)',
    BODY,
), "SR3: saveRaw 2xx branch must await _refreshFromDisk() then flashSaved()"

print(
    "PASS  SR1 + SR2 + SR3: saveRaw hides raw error then PUTs text/plain; 422 "
    "renders Line N, col M format; 2xx refreshes from disk + flashes Saved"
)
