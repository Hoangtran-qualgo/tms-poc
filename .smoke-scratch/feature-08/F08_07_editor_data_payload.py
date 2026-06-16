# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP6 -- embedded #editor-data JSON payload.

Render the editor and verify the <script id="editor-data"> block:
  - has `type="application/json"`
  - carries valid JSON with keys `path`, `file_name`, `feature`, `raw`
  - `feature` is the Feature.to_dict() shape (background, scenario,
    tags, enums)
  - `raw` is the canonical Gherkin source for the on-disk file

This is the contract `tmsEditor.boot()` consumes via JSON.parse.
"""
import html as html_lib
import json
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
        json={
            "parent": "Alpha/Mod",
            "file_name": "case",
            "scenario_name": "seed scenario",
            "description": "seed description",
        },
    )
    page = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)


m = re.search(
    r'<script[^>]*id="editor-data"([^>]*)>([\s\S]*?)</script>', page
)
assert m, "TP6: rendered editor must include <script id='editor-data'>"

attrs, body = m.group(1), m.group(2).strip()
assert 'type="application/json"' in attrs, (
    f"TP6: #editor-data must declare type='application/json'; got attrs={attrs!r}"
)

# Jinja `|tojson` HTML-escapes ampersands; un-escape before JSON.parse.
data = json.loads(html_lib.unescape(body))
for key in ("path", "file_name", "feature", "raw"):
    assert key in data, (
        f"TP6: #editor-data payload must carry key {key!r}; "
        f"got keys={sorted(data.keys())!r}"
    )

assert data["path"] == "Alpha/Mod/case.feature", (
    f"TP6: editor-data.path must be the request path; got {data['path']!r}"
)
assert data["file_name"] == "case.feature", (
    f"TP6: editor-data.file_name must be the leaf; got {data['file_name']!r}"
)

# `feature` is Feature.to_dict()-shaped.
feat = data["feature"]
assert isinstance(feat, dict), "TP6: editor-data.feature must be a JSON object"
for sub in ("description", "tags", "background", "scenario"):
    assert sub in feat, (
        f"TP6: editor-data.feature must carry {sub!r} "
        f"(Feature.to_dict() shape); got keys={sorted(feat.keys())!r}"
    )
assert feat["description"] == "seed description", (
    f"TP6: editor-data.feature.description must round-trip; "
    f"got {feat['description']!r}"
)
assert "steps" in feat["background"], (
    "TP6: editor-data.feature.background must carry `steps`"
)
for sub in ("kind", "name", "tags", "steps", "examples"):
    assert sub in feat["scenario"], (
        f"TP6: editor-data.feature.scenario must carry {sub!r}; "
        f"got keys={sorted(feat['scenario'].keys())!r}"
    )

# `raw` is the on-disk Gherkin text.
assert isinstance(data["raw"], str) and "Feature:" in data["raw"], (
    f"TP6: editor-data.raw must be the Gherkin source string; "
    f"got {data['raw']!r}"
)

print(
    "PASS  TP6: #editor-data is a JSON script block with valid JSON carrying "
    "path / file_name / feature (Feature.to_dict shape) / raw (Gherkin source)"
)
