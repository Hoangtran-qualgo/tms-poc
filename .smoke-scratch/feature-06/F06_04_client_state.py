# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Client state (CS1-CS3) -- Hybrid.

Per Step-1 sign-off Q1, JS-runtime rules are tested via a Hybrid
approach:
  - Static: regex over `app/static/app.js` source for function
    bodies + Set-mutation branches + event-listener wiring.
  - Render-and-grep: hit `/ui/tree` and assert the caret's inline
    `onclick` invokes `toggleTreeFolder(...)`.
  - DOM-parse: extract `data-path` attributes from /ui/tree HTML
    and assert each folder row carries one (so `tmsRestoreTreeState`
    has something to walk).
"""
import pathlib
import re
import tempfile

from app import create_app


REPO = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO / "app" / "static" / "app.js").read_text()


def _extract_block(src: str, sig_pattern: str) -> str:
    """Return the brace-balanced body of the first match for `sig_pattern`."""
    m = re.search(sig_pattern, src)
    assert m, f"static-JS: signature pattern not found: {sig_pattern!r}"
    start = src.index("{", m.end() - 1)
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"unbalanced braces after {sig_pattern!r}")


# --- CS1: const tmsExpandedFolders = new Set() at module scope ---------
assert re.search(
    r"^const\s+tmsExpandedFolders\s*=\s*new\s+Set\s*\(\s*\)\s*;",
    JS,
    re.MULTILINE,
), (
    "CS1: app.js must declare `const tmsExpandedFolders = new Set()` at "
    "module scope (top-level, not inside a function). The Set must survive "
    "tree re-renders."
)
print("PASS  CS1 (static): const tmsExpandedFolders = new Set() at module scope")


# --- CS2: toggleTreeFolder(rowEl) mutates the Set on the right branches.
body = _extract_block(JS, r"function\s+toggleTreeFolder\s*\(\s*rowEl\s*\)")
assert "tmsExpandedFolders.add(path)" in body, (
    "CS2 (static): toggleTreeFolder() must call tmsExpandedFolders.add(path) "
    "on the expand branch"
)
assert "tmsExpandedFolders.delete(path)" in body, (
    "CS2 (static): toggleTreeFolder() must call tmsExpandedFolders.delete(path) "
    "on the collapse branch"
)
# The add/delete must be guarded by the toggled `hidden` state, so the
# direction is unambiguous (expand -> add, collapse -> delete).
assert re.search(
    r"if\s*\(\s*isHidden\s*\)\s*tmsExpandedFolders\.delete\s*\(\s*path\s*\)",
    body,
), (
    "CS2 (static): the Set mutation must be guarded by `if (isHidden) "
    "tmsExpandedFolders.delete(path)` so collapse removes the path and "
    "expand adds it"
)

# Render-and-grep: the caret button's inline onclick must wire to
# toggleTreeFolder. Without a real seeded FS this is the strongest
# render-side proof short of a JS runtime.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    html = client.get("/ui/tree").get_data(as_text=True)

caret_onclick = re.search(
    r'<button[^>]*class="caret[^"]*"[^>]*onclick="[^"]*toggleTreeFolder\(',
    html,
)
assert caret_onclick, (
    "CS2 (render-and-grep): the caret <button> in /ui/tree HTML must carry "
    "an inline onclick that invokes toggleTreeFolder(...) (no event listener; "
    "the spec mandates an inline onclick attribute)"
)
print("PASS  CS2 (Hybrid): toggleTreeFolder mutates Set on expand/collapse + caret wires inline onclick")


# --- CS3: tmsRestoreTreeState walks #tree-pane .tree-folder + afterSwap.
body = _extract_block(JS, r"function\s+tmsRestoreTreeState\s*\(\s*\)")
assert '"#tree-pane .tree-folder"' in body, (
    "CS3 (static): tmsRestoreTreeState() must querySelectorAll "
    "`#tree-pane .tree-folder` (so it only walks the current tree pane, "
    "not the test-run sibling pane)"
)
assert "tmsExpandedFolders.has(path)" in body, (
    "CS3 (static): tmsRestoreTreeState() must consult tmsExpandedFolders.has(path) "
    "to decide which rows to re-expand"
)

# htmx:afterSwap listener wired to call tmsRestoreTreeState when
# #tree-pane is the swap target.
afterswap = re.search(
    r'document\.body\.addEventListener\s*\(\s*"htmx:afterSwap"\s*,'
    r'.*?if\s*\([^)]*e\.target\.id\s*===\s*"tree-pane"\s*\)'
    r'\s*\{\s*tmsRestoreTreeState\(\)',
    JS,
    re.DOTALL,
)
assert afterswap, (
    "CS3 (static): app.js must register a `document.body.addEventListener("
    "\"htmx:afterSwap\", ...)` listener whose handler calls "
    "tmsRestoreTreeState() when e.target.id === \"tree-pane\""
)

# Render-and-grep + DOM-parse: every folder row must carry data-path
# for the restore walk.
folder_rows = re.findall(
    r'<div[^>]*class="tree-folder[^"]*"[^>]*data-path="([^"]+)"',
    html,
)
assert "Alpha" in folder_rows and "Alpha/Mod" in folder_rows, (
    f"CS3 (DOM-parse): every folder row must carry a data-path attribute "
    f"so tmsRestoreTreeState() can walk them; got {folder_rows!r}"
)
print("PASS  CS3 (Hybrid): tmsRestoreTreeState walks #tree-pane .tree-folder; htmx:afterSwap wired; rows carry data-path")
