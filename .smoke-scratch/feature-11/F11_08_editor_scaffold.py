"""S3.2 smoke — file editor HTML scaffold for the Enums section.

Asserts that GET /ui/file/<p> for an existing .feature file renders:
1. The new <div id="feature-enums"> wrapper with data-section="enums".
2. All four id'd sub-elements: missing-state, empty-state hint,
   pickers container, orphans container.
3. The "Initialize enums file" button id, present (but hidden by default).
4. The legacy structured-tab elements (feature-description,
   feature-tags-chips, background-card) still render — no regression.
5. The initial editor-data JSON payload still carries `feature` so the
   controller has the per-feature enums to render from.
"""
import json
import pathlib
import re
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "pay.feature"], description="Pay")

    client = app.test_client()
    r = client.get("/ui/file/Alpha/Checkout/pay.feature")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

# --- 1. Section wrapper ---------------------------------------------------
assert 'id="feature-enums"' in html, "feature-enums wrapper missing"
assert 'data-section="enums"' in html, "data-section attr missing"
print("PASS  Enums section wrapper #feature-enums present")

# --- 2. Sub-elements ------------------------------------------------------
for sub_id in (
    "feature-enums-missing",
    "feature-enums-empty",
    "feature-enums-pickers",
    "feature-enums-orphans",
):
    assert f'id="{sub_id}"' in html, f"{sub_id} missing"
print("PASS  All four sub-element ids present (missing, empty, pickers, orphans)")

# --- 3. Initialize button -------------------------------------------------
assert 'id="feature-enums-init-btn"' in html, "init button missing"
assert "Initialize enums file" in html, "init button label missing"
# Missing-state wrapper must start hidden (controller decides whether to show).
m = re.search(
    r'id="feature-enums-missing"\s+class="([^"]+)"', html
)
assert m and "hidden" in m.group(1), m
print("PASS  Initialize button present; missing-state wrapper starts hidden")

# --- 4. No regression on legacy structured-tab ids ------------------------
for legacy_id in (
    "feature-description",
    "feature-tags-chips",
    "background-card",
    "scenario-name",
    "scenario-steps",
    "tab-structured",
    "tab-raw",
):
    assert f'id="{legacy_id}"' in html, f"regression: {legacy_id} missing"
print("PASS  Legacy structured-tab elements untouched")

# --- 5. editor-data payload still carries feature dict --------------------
m = re.search(
    r'<script id="editor-data" type="application/json">\s*(.*?)\s*</script>',
    html,
    flags=re.DOTALL,
)
assert m, "editor-data script block missing"
payload = json.loads(m.group(1))
assert "feature" in payload, list(payload.keys())
# Feature.to_dict() now includes enums; the freshly-created file has {}
assert payload["feature"]["enums"] == {}, payload["feature"]["enums"]
print("PASS  editor-data carries feature.enums (== {} for fresh file)")
