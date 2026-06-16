# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP3 -- tab buttons.

Render the editor and confirm both tab buttons (#tab-btn-structured,
#tab-btn-raw) are present with the right initial active state:
structured is active (border-slate-800 + text-slate-800), raw is
inactive (border-transparent + text-slate-500). Both visible labels
match the spec.
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
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "x"},
    )
    html = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)


def _btn(id_: str) -> tuple[str, str]:
    m = re.search(
        rf'<button[^>]*id="{re.escape(id_)}"[^>]*class="([^"]*)"[^>]*>([\s\S]*?)</button>',
        html,
    )
    assert m, f"TP3: tab button #{id_} must render"
    return m.group(1), m.group(2).strip()


cls_struct, label_struct = _btn("tab-btn-structured")
cls_raw, label_raw = _btn("tab-btn-raw")

assert label_struct == "Structured", (
    f"TP3: #tab-btn-structured label must be 'Structured'; got {label_struct!r}"
)
assert label_raw == "Raw", (
    f"TP3: #tab-btn-raw label must be 'Raw'; got {label_raw!r}"
)

# Initial state: structured active, raw inactive.
assert "border-slate-800" in cls_struct and "text-slate-800" in cls_struct, (
    "TP3: #tab-btn-structured must render initially active "
    "(border-slate-800 + text-slate-800)"
)
assert "border-transparent" in cls_raw and "text-slate-500" in cls_raw, (
    "TP3: #tab-btn-raw must render initially inactive "
    "(border-transparent + text-slate-500)"
)

# Tab content containers: tab-structured visible, tab-raw hidden.
assert re.search(
    r'<div[^>]*id="tab-structured"[^>]*class="(?:(?!\bhidden\b)[^"])*"', html
), "TP3: #tab-structured container must NOT carry `hidden` initially"
assert re.search(
    r'<div[^>]*id="tab-raw"[^>]*class="[^"]*\bhidden\b[^"]*"', html
), "TP3: #tab-raw container must carry `hidden` initially"

print("PASS  TP3: tab buttons + content containers render with correct initial active state (structured)")
