# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / UI triggers (UI1-UI5).

Static-text inspection of `app/static/app.js`. Per the feature-04
Step-1 sign-off, smokes do NOT spin up a Javascript runtime; they
verify the documented entry-point shapes by regex-matching the source
text. Each UI* row maps to one regex-bundle.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


def _extract_block(js: str, signature_re: str, contains: str | None = None) -> str:
    """Return the body of the first `{ … }` block following the signature.

    When ``contains`` is given, scan all signature matches and return the
    first body whose text contains the substring. This disambiguates the
    multiple `async save()` / `async move()` / `async rename()` defined
    across the file (file editor vs run editor).
    """
    flags = re.DOTALL
    for m in re.finditer(signature_re, js, flags=flags):
        start = js.index("{", m.end() - 1)
        depth = 0
        for i in range(start, len(js)):
            c = js[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = js[start : i + 1]
                    if contains is None or contains in body:
                        return body
                    break
    raise AssertionError(
        f"signature {signature_re!r} not found"
        + (f" with `{contains}` in body" if contains else "")
    )


# --- UI1: tmsCreateFile(parent) --------------------------------------------
body1 = _extract_block(JS, r"function\s+tmsCreateFile\s*\(\s*parent\s*\)")
assert "tmsOpenModal" in body1, (
    "UI1: tmsCreateFile(parent) must use tmsOpenModal (not window.prompt)"
)
# Three-field form (tech-04 D2/D3): file name + feature description
# (optional) + scenario name (required).
assert re.search(r"""tms-cf-name""", body1), (
    "UI1: tmsCreateFile must render a file-name input (`tms-cf-name`)"
)
assert re.search(r"""tms-cf-desc""", body1), (
    "UI1: tmsCreateFile must render a description input (`tms-cf-desc`)"
)
assert re.search(r"""tms-cf-scenario""", body1), (
    "UI1: tmsCreateFile must render a scenario-name input (`tms-cf-scenario`)"
)
# Modal hint declares `.feature` auto-append (verbatim copy in v1).
assert ".feature is added automatically" in body1, (
    "UI1: tmsCreateFile modal must carry the '.feature is added automatically' hint"
)
# POST /api/files with {parent, file_name, scenario_name, description}.
assert re.search(
    r"""tmsApiPost\(\s*["']/api/files["']""", body1,
), (
    "UI1: tmsCreateFile must call tmsApiPost('/api/files', …)"
)
assert (
    re.search(r"\bparent\s*[,}]", body1)
    and "file_name" in body1
    and "scenario_name" in body1
    and "description" in body1
), (
    "UI1: tmsCreateFile POST body must carry parent, file_name, "
    "scenario_name, description"
)
# Confirm gate keys on file name + scenario name (description optional).
assert "!(n && sc)" in body1, (
    "UI1: Confirm must gate on file name + scenario name (not description)"
)
print(
    "PASS  UI1: tmsCreateFile(parent) -> tmsOpenModal + POST /api/files "
    "{parent, file_name, scenario_name, description}; gated on name + scenario"
)


# --- UI2: tmsEditor.rename() -----------------------------------------------
# Multiple `async rename()` methods may exist (file editor vs run editor);
# select the one whose body references /api/files/<path>/rename.
body2 = _extract_block(
    JS, r"async\s+rename\s*\(\s*\)", contains="/api/files/"
)
assert "/rename" in body2, (
    "UI2: tmsEditor.rename() body must target the /rename sub-route"
)
assert re.search(r"""method\s*:\s*["']PATCH["']""", body2), (
    "UI2: tmsEditor.rename() must issue a PATCH request"
)
assert re.search(r"""/api/files/["']?\s*\+\s*this\.state\.path\s*\+\s*["']/rename""", body2), (
    "UI2: tmsEditor.rename() must target /api/files/<state.path>/rename"
)
assert re.search(r"""file_name\s*:""", body2), (
    "UI2: tmsEditor.rename() request body must carry {file_name: …}"
)
print("PASS  UI2: tmsEditor.rename() -> PATCH /api/files/<state.path>/rename {file_name}")


# --- UI3: tmsEditor.move() -------------------------------------------------
body3 = _extract_block(
    JS, r"async\s+move\s*\(\s*\)", contains="/api/files/"
)
assert "/move" in body3, (
    "UI3: tmsEditor.move() body must target the /move sub-route"
)
assert "tmsOpenModal" in body3, (
    "UI3: tmsEditor.move() must open a modal via tmsOpenModal (tree-based folder picker)"
)
assert re.search(r"""method\s*:\s*["']PATCH["']""", body3), (
    "UI3: tmsEditor.move() must issue a PATCH request"
)
assert re.search(r"""/api/files/["']?\s*\+\s*sourcePath\s*\+\s*["']/move""", body3), (
    "UI3: tmsEditor.move() must target /api/files/<state.path>/move"
)
assert re.search(r"""parent\s*:\s*destParent""", body3), (
    "UI3: tmsEditor.move() request body must carry {parent: destParent}"
)
# Confirm the picker is built from /api/tree (spec says "tree-based folder picker").
assert re.search(r"""/api/tree""", body3), (
    "UI3: tmsEditor.move() picker must hydrate from /api/tree"
)
print("PASS  UI3: tmsEditor.move() -> tmsOpenModal picker + PATCH /api/files/<state.path>/move {parent}")


# --- UI4: tmsEditor.save() -------------------------------------------------
# Two `async save()` exist (file editor vs run editor). Pick the file-editor
# one by requiring /api/files/ in the body.
body4 = _extract_block(
    JS, r"async\s+save\s*\(\s*\)", contains="/api/files/"
)
assert re.search(r"""method\s*:\s*["']PATCH["']""", body4), (
    "UI4: tmsEditor.save() must issue a PATCH request"
)
assert re.search(
    r"""/api/files/["']?\s*\+\s*this\.state\.path""", body4
), (
    "UI4: tmsEditor.save() must target /api/files/<state.path>"
)
assert re.search(r"""JSON\.stringify\(this\.state\.feature\)""", body4), (
    "UI4: tmsEditor.save() body must be JSON.stringify(this.state.feature) (structured buffer)"
)
# Confirm save delegates to saveRaw when on the raw tab.
assert re.search(r"""this\.state\.tab\s*===?\s*["']raw["']""", body4) and "saveRaw" in body4, (
    "UI4: tmsEditor.save() must delegate to saveRaw() when state.tab === 'raw'"
)
print("PASS  UI4: tmsEditor.save() -> PATCH /api/files/<state.path> with JSON.stringify(state.feature)")


# --- UI5: tmsEditor.saveRaw() ----------------------------------------------
body5 = _extract_block(JS, r"async\s+saveRaw\s*\(\s*\)")
assert re.search(r"""method\s*:\s*["']PUT["']""", body5), (
    "UI5: tmsEditor.saveRaw() must issue a PUT request"
)
assert re.search(
    r"""/api/files/["']?\s*\+\s*this\.state\.path\s*\+\s*["']/raw""", body5
), (
    "UI5: tmsEditor.saveRaw() must target /api/files/<state.path>/raw"
)
assert re.search(r"""body\s*:\s*this\.state\.raw""", body5), (
    "UI5: tmsEditor.saveRaw() body must be this.state.raw (raw textarea contents)"
)
print("PASS  UI5: tmsEditor.saveRaw() -> PUT /api/files/<state.path>/raw with state.raw")


# --- UI button wiring: btn-rename / btn-move / btn-save / btn-save-raw -----
# Sanity: confirm the topbar buttons are wired to the editor methods so
# the UI rules above translate into actual user-visible affordances.
# Look for `getElementById("btn-<id>")` paired with the editor method call.
for btn, method_re in (
    ("btn-rename", r"\.rename\s*\("),
    ("btn-move", r"\.move\s*\("),
    ("btn-save", r"\.save\s*\("),
    ("btn-save-raw", r"\.saveRaw\s*\("),
):
    pat = re.compile(
        rf"""getElementById\(\s*["']{re.escape(btn)}["']\s*\)[\s\S]{{0,200}}?{method_re}""",
    )
    assert pat.search(JS), (
        f"UI sanity: topbar button {btn!r} must wire a click handler to a "
        f"method matching {method_re!r}"
    )
print("PASS  UI sanity: btn-rename / btn-move / btn-save / btn-save-raw wired to editor methods")
