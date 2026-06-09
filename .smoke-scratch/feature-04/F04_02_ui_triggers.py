# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / UI triggers (UI1-UI3).

Static-text inspection of `app/static/app.js`. Per Step-1 sign-off
note 2, smokes do NOT spin up a Javascript runtime; they verify that
the three documented entry-point functions exist with the documented
contract by regex-matching the source text. The folder views
(`folder_root.html`, `folder_project.html`, `folder_module.html`,
`folder_subfolder.html`) embed the call sites; verifying the function
bodies is the strongest static check available without a JS engine.
"""
import pathlib
import re


JS = (pathlib.Path(__file__).resolve().parents[2]
      / "app" / "static" / "app.js").read_text()


def _extract_function_body(js: str, signature_pattern: str) -> str:
    """Return the body of the first function whose signature matches.

    Uses simple brace counting to find the matching `}` for the opening
    `{`. Sufficient for these top-level `async function name(args) { … }`
    declarations.
    """
    m = re.search(signature_pattern, js)
    assert m, f"signature not found: {signature_pattern!r}"
    start = js.index("{", m.end() - 1)
    depth = 0
    for i in range(start, len(js)):
        c = js[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return js[start : i + 1]
    raise AssertionError(f"unbalanced braces after signature {signature_pattern!r}")


# --- UI1: tmsCreateProject() -------------------------------------------------
body1 = _extract_function_body(JS, r"async\s+function\s+tmsCreateProject\s*\(\s*\)")
assert "window.prompt" in body1, (
    "UI1: tmsCreateProject() must use window.prompt to collect the project name"
)
assert re.search(
    r"""tmsApiPost\(\s*["']/api/folders["']\s*,\s*\{\s*parent\s*:\s*["']{2}\s*,\s*name\s*\}""",
    body1,
), (
    "UI1: tmsCreateProject() must call tmsApiPost('/api/folders', { parent: '', name })"
)
assert re.search(r"""tmsRefreshFolder\(\s*["']{2}\s*\)""", body1), (
    "UI1: tmsCreateProject() must call tmsRefreshFolder('') after a successful POST"
)
print("PASS  UI1: tmsCreateProject() -> prompt + POST /api/folders {parent: '', name} + tmsRefreshFolder('')")


# --- UI2: tmsCreateModule(project) ------------------------------------------
body2 = _extract_function_body(JS, r"async\s+function\s+tmsCreateModule\s*\(\s*project\s*\)")
assert "window.prompt" in body2, (
    "UI2: tmsCreateModule(project) must use window.prompt to collect the module name"
)
assert re.search(
    r"""tmsApiPost\(\s*["']/api/folders["']\s*,\s*\{\s*parent\s*:\s*project\s*,\s*name\s*\}""",
    body2,
), (
    "UI2: tmsCreateModule(project) must call tmsApiPost('/api/folders', { parent: project, name })"
)
assert re.search(r"tmsRefreshFolder\(\s*project\s*\)", body2), (
    "UI2: tmsCreateModule(project) must call tmsRefreshFolder(project) after a successful POST"
)
print("PASS  UI2: tmsCreateModule(project) -> prompt + POST /api/folders {parent: project, name} + tmsRefreshFolder(project)")


# --- UI3: tmsCreateSubfolder(parent) ----------------------------------------
# Spec says "tmsOpenModal-based" but the as-shipped code uses
# window.prompt (spec gap surfaced in COVERAGE.md). Test follows code.
body3 = _extract_function_body(JS, r"async\s+function\s+tmsCreateSubfolder\s*\(\s*parent\s*\)")
assert "window.prompt" in body3, (
    "UI3: tmsCreateSubfolder(parent) must use window.prompt (spec says tmsOpenModal -- known spec gap)"
)
assert re.search(
    r"""tmsApiPost\(\s*["']/api/folders["']\s*,\s*\{\s*parent\s*,\s*name\s*\}""",
    body3,
), (
    "UI3: tmsCreateSubfolder(parent) must call tmsApiPost('/api/folders', { parent, name })"
)
assert re.search(r"tmsRefreshFolder\(\s*parent\s*\)", body3), (
    "UI3: tmsCreateSubfolder(parent) must call tmsRefreshFolder(parent) after a successful POST"
)
print("PASS  UI3: tmsCreateSubfolder(parent) -> prompt + POST /api/folders {parent, name} + tmsRefreshFolder(parent)")
