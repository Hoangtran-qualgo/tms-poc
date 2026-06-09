# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Expanded-state preservation (EP1-EP3) -- Hybrid.

Per Step-1 sign-off Q1, JS-runtime DOM-event rules use a Hybrid test:
  - Static: regex over `app/static/app.js` for the function-body shape
    and the `htmx:afterSwap` listener wiring.
  - Render-and-grep: hit /ui/tree and assert the caret's inline onclick
    invokes toggleTreeFolder (proves the EP1 mutation path is wired).
  - DOM-parse: re.findall data-path attributes for the rows
    tmsRestoreTreeState walks.

EP1, EP2 share most of their static surface with CS2 / CS3 but frame the
claim differently: EP* is about *state preservation across re-renders*,
CS* is about *the function bodies themselves*.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO / "app" / "static" / "app.js").read_text()


def _extract_block(src: str, sig_pattern: str) -> str:
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


# --- EP1: caret toggle MUTATES tmsExpandedFolders (add/delete). ---------
toggle = _extract_block(JS, r"function\s+toggleTreeFolder\s*\(\s*rowEl\s*\)")
# Both mutations are required; their direction is locked by `isHidden`.
assert re.search(
    r"if\s*\(\s*isHidden\s*\)\s*tmsExpandedFolders\.delete\s*\(\s*path\s*\)\s*;\s*"
    r"else\s+tmsExpandedFolders\.add\s*\(\s*path\s*\)\s*;",
    toggle,
), (
    "EP1 (static): toggleTreeFolder() must mutate tmsExpandedFolders in BOTH "
    "directions guarded by `isHidden` -- `if (isHidden) ...delete(path); "
    "else ...add(path);` -- so the Set tracks the live state."
)

# Render-and-grep: the caret's inline onclick wires the mutation path.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    html = client.get("/ui/tree").get_data(as_text=True)
caret = re.search(
    r'<button[^>]*class="caret[^"]*"[^>]*'
    r'onclick="event\.stopPropagation\(\);\s*toggleTreeFolder\([^)]*\)"',
    html,
)
assert caret, (
    "EP1 (render): caret <button> must wire onclick="
    "\"event.stopPropagation(); toggleTreeFolder(...)\" so each click reaches "
    "the Set-mutation code path"
)
print("PASS  EP1 (Hybrid): toggleTreeFolder mutates tmsExpandedFolders in both directions; caret onclick wired")


# --- EP2: htmx:afterSwap on #tree-pane -> tmsRestoreTreeState; walks
# `[data-path]` rows. ---
restore = _extract_block(JS, r"function\s+tmsRestoreTreeState\s*\(\s*\)")
assert 'querySelectorAll("#tree-pane .tree-folder")' in restore, (
    "EP2 (static): tmsRestoreTreeState() must walk "
    "`document.querySelectorAll(\"#tree-pane .tree-folder\")`"
)
assert "row.dataset.path" in restore, (
    "EP2 (static): tmsRestoreTreeState() must read each row's "
    "`dataset.path` (the data-path attribute) to look up the Set"
)
# htmx:afterSwap wiring + the if-branch guarding the call.
afterswap_to_restore = re.search(
    r'document\.body\.addEventListener\s*\(\s*"htmx:afterSwap".*?'
    r'e\.target\.id\s*===\s*"tree-pane"\s*\)\s*\{\s*tmsRestoreTreeState\s*\(\s*\)\s*;',
    JS,
    re.DOTALL,
)
assert afterswap_to_restore, (
    "EP2 (static): the body-level `htmx:afterSwap` listener must call "
    "tmsRestoreTreeState() when e.target.id === \"tree-pane\""
)

# DOM-parse: every folder row carries data-path so tmsRestoreTreeState's
# walk is well-defined.
folder_paths = re.findall(
    r'<div[^>]*class="tree-folder[^"]*"[^>]*data-path="([^"]+)"',
    html,
)
assert folder_paths == ["Alpha", "Alpha/Mod"] or set(["Alpha", "Alpha/Mod"]).issubset(
    set(folder_paths)
), (
    f"EP2 (DOM-parse): rendered /ui/tree must carry data-path on every "
    f"folder row (so tmsRestoreTreeState's walk has a key); got {folder_paths!r}"
)
print("PASS  EP2 (Hybrid): htmx:afterSwap -> tmsRestoreTreeState; walks #tree-pane .tree-folder; rows carry data-path")


# --- EP3: rows that disappeared between renders simply drop off. -------
# The guard `if (!path || !tmsExpandedFolders.has(path)) return;` is the
# whole story: nothing to do for rows whose path is gone from the DOM
# (and nothing to do for rows whose path was never expanded). No
# explicit clean-up of the Set is needed -- the Set may keep stale
# entries; when the path returns it will re-expand, otherwise it just
# sits unused. Static check is the strongest available without a JS
# runtime.
assert re.search(
    r"if\s*\(\s*!path\s*\|\|\s*!tmsExpandedFolders\.has\s*\(\s*path\s*\)\s*\)\s*return\s*;",
    restore,
), (
    "EP3 (static): tmsRestoreTreeState() must guard with "
    "`if (!path || !tmsExpandedFolders.has(path)) return;` so rows whose "
    "data-path is missing or was never expanded simply drop off (no "
    "exception, no bespoke cleanup)"
)
print("PASS  EP3 (static): guard `if (!path || !tmsExpandedFolders.has(path)) return` covers disappeared rows")
