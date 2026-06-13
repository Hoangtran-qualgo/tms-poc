# Pattern: see .smoke-scratch/README.md
"""tech-04 / testcase-detail-revamp / D5 -- Enums redesigned as a row grid.

Static JS inspection of the new enums controller in app/static (the file
editor). D5 replaces the "one <select> per defined kind" model with an
up-to-3-column grid of (kind, value) rows:
  - `renderEnums` (status 'ok') delegates to `_renderEnumRows`.
  - `_renderEnumRows` builds a 3-column grid + a "+ Add enum" button, and
    pre-fills one row per assigned, in-vocab enum entry.
  - `_buildEnumRow` renders a kind <select> + value <select> + remove (×);
    the kind <select> excludes kinds already used by OTHER rows (OQ6).
  - `_commitEnumRows` rebuilds feature.enums from the rows and PRESERVES
    orphan entries (kind not in the current vocab).
The shared container ids are unchanged, so F11_08 still pins the scaffold.
"""
import pathlib
import re
import tempfile

from app import create_app


JS = "\n".join(
    _p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js"))
)


def _block(name_re):
    m = re.search(name_re + r"\s*\{.*?\n  \},", JS, re.DOTALL)
    assert m, f"method matching {name_re!r} must be defined"
    return m.group(0)


# --- renderEnums (ok branch) delegates to the grid builder. --------------
render = _block(r"renderEnums\(\)")
assert "this._renderEnumRows(vocab)" in render, (
    "D5: renderEnums must delegate the 'ok' branch to _renderEnumRows(vocab)"
)

# --- _renderEnumRows: 3-col grid + '+ Add enum' + pre-fill from enums. ----
rows = _block(r"_renderEnumRows\(vocab\)")
assert "lg:grid-cols-3" in rows, "D5: enum rows must lay out in an up-to-3-column grid"
assert 'dataset.action = "add-enum"' in rows and "+ Add enum" in rows, (
    "D5: _renderEnumRows must render a '+ Add enum' control"
)
assert "kind in vocab" in rows, (
    "D5: pre-filled rows come from assigned, in-vocab enum entries"
)
assert re.search(r'rows\.push\(\{\s*kind:\s*""\s*,\s*value:\s*""\s*\}\)', rows), (
    "D5: a single blank row is the default when nothing is assigned"
)

# --- _buildEnumRow: kind + value selects + remove; OQ6 kind exclusion. ----
row = _block(r"_buildEnumRow\(row, vocab\)")
assert 'dataset.field = "enum-kind"' in row, "D5: each row has a kind <select>"
assert 'dataset.field = "enum-value"' in row, "D5: each row has a value <select>"
assert 'dataset.action = "remove-enum"' in row, "D5: each row has a remove (×) control"
assert "usedByOthers" in row and "if (usedByOthers.has(kind)) continue" in row, (
    "OQ6: the kind <select> must exclude kinds already used by other rows"
)

# --- _commitEnumRows preserves orphans (kind not in vocab). --------------
commit = _block(r"_commitEnumRows\(\)")
assert "this.state.feature.enums = next" in commit, (
    "D5: _commitEnumRows rebuilds feature.enums from the visible rows"
)
assert "!(kind in vocab)" in commit, (
    "D5: _commitEnumRows must preserve orphan entries (kind not in vocab)"
)

# --- Integration: the four enums container ids still render (F11_08 scaffold). ---
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "c", "scenario_name": "S"},
    )
    html = client.get("/ui/file/Alpha/Mod/c.feature").get_data(as_text=True)
for sub_id in (
    "feature-enums-pickers",
    "feature-enums-orphans",
    "feature-enums-missing",
    "feature-enums-empty",
):
    assert f'id="{sub_id}"' in html, f"D5: container {sub_id} must still render"

print("PASS  D5: Enums render as a 3-column (kind, value) row grid with +Add/remove, OQ6 kind exclusion, orphan-preserving commit; scaffold ids intact")
