# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / AC7 -- Saved badge flashes ~1.5s; cleared on edit.

Static inspection of:
  - flashSaved(): targets #saved-indicator, removes hidden, setTimeout
    1500 ms to re-hide.
  - markDirty(): when dirty, calls _hideSavedBadge() so a fresh edit
    clears any lingering badge.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


def _body(sig: str, contains: str | None = None) -> str:
    for m in re.finditer(sig, JS, flags=re.DOTALL):
        start = JS.index("{", m.end() - 1)
        depth = 0
        for i in range(start, len(JS)):
            c = JS[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = JS[start:i + 1]
                    if contains is None or contains in body:
                        return body
                    break
    raise AssertionError(f"signature {sig!r} (contains={contains!r}) not found")


# --- flashSaved: file-editor version targets #saved-indicator. ---
flash = _body(r"flashSaved\s*\(\s*\)", contains='"saved-indicator"')
assert 'getElementById("saved-indicator")' in flash, (
    "AC7: file-editor flashSaved must target #saved-indicator"
)
assert 'el.classList.remove("hidden")' in flash, (
    "AC7: flashSaved must un-hide the Saved badge"
)
# 1500 ms timer literal -- drift flagged if changed.
assert re.search(
    r'setTimeout\(\s*\(\s*\)\s*=>\s*\{[\s\S]+?\}\s*,\s*1500\s*\)', flash
), (
    "AC7: flashSaved must setTimeout with 1500 ms literal (spec says '~1.5 s')"
)
# Hide after timer fires.
assert re.search(
    r'el\.classList\.add\(\s*"hidden"\s*\)', flash
), "AC7: setTimeout body must re-hide #saved-indicator"
# Clear any prior timer so back-to-back saves don't stack.
assert "clearTimeout" in flash, (
    "AC7: flashSaved must clearTimeout any in-flight _savedTimer"
)


# --- markDirty -> clears Saved badge when dirty. ---
md = _body(r"markDirty\s*\(\s*d\s*\)")
assert re.search(
    r'if\s*\(\s*this\.state\.dirty\s*\)\s*this\._hideSavedBadge\(\s*\)', md
), "AC7: markDirty must call _hideSavedBadge() when becoming dirty"


# --- _hideSavedBadge actually hides + cancels the timer. ---
hide = _body(r"_hideSavedBadge\s*\(\s*\)", contains='"saved-indicator"')
assert re.search(
    r'el\.classList\.add\(\s*"hidden"\s*\)', hide
), "AC7: _hideSavedBadge must hide #saved-indicator"
assert "clearTimeout" in hide, (
    "AC7: _hideSavedBadge must clearTimeout the pending re-hide timer"
)

print("PASS  AC7: flashSaved un-hides #saved-indicator with 1500 ms re-hide timer; markDirty(true) clears it immediately via _hideSavedBadge")
