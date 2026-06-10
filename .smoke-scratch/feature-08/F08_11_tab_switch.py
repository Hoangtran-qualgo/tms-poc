# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TS1 + TS2 + TS3 -- tab switching.

TS1: switchTab(target) is a no-op when target === state.tab; otherwise
    swaps visible content but the buffer is shared.
TS2: dirty-buffer switch shows window.confirm with the spec literal;
    Cancel aborts; OK resets BOTH `feature` (from snapshotJson) AND
    `raw` (from snapshotRaw), markDirty(false), re-renders both tabs.
TS3: save() dispatches to saveRaw() when state.tab === 'raw'.

Cross-credit (TS3): feature-05/F05_02_ui_triggers.py UI4 already
asserts the dispatch literal. This file owns the controller side and
adds the early-return + JSON.parse(snapshotJson) assertions.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


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


# --- TS1: switchTab no-op when target === state.tab. ---
sw = _body(r"switchTab\s*\(\s*target\s*\)")
assert re.search(
    r'if\s*\(\s*this\.state\.tab\s*===?\s*target\s*\)\s*return', sw
), "TS1: switchTab must early-return when target === state.tab"

# Visible content swap: toggle hidden on #tab-structured and #tab-raw.
assert re.search(
    r'getElementById\(\s*"tab-structured"\s*\)\.classList\.toggle\(\s*"hidden"', sw
), "TS1: switchTab must toggle #tab-structured hidden class"
assert re.search(
    r'getElementById\(\s*"tab-raw"\s*\)\.classList\.toggle\(\s*"hidden"', sw
), "TS1: switchTab must toggle #tab-raw hidden class"

# Buffer is shared: state.tab is reassigned, not state.feature/state.raw,
# in the post-confirm dispatch.
assert re.search(r'this\.state\.tab\s*=\s*target', sw), (
    "TS1: switchTab must reassign state.tab (the buffer itself is shared)"
)


# --- TS2: dirty-buffer confirm + reset to snapshots. ---
assert re.search(r'if\s*\(\s*this\.state\.dirty\s*\)', sw), (
    "TS2: switchTab must branch on state.dirty"
)
assert re.search(
    r'window\.confirm\(\s*\n?\s*"You have unsaved changes in the current tab\. "',
    sw,
), "TS2: switchTab must call window.confirm with the spec literal opener"
assert (
    '"Switching tabs will discard them. Continue?"' in sw
), "TS2: confirm message must include the 'Switching tabs will discard them.' literal"
assert re.search(
    r'if\s*\(\s*!\s*ok\s*\)\s*return', sw
), "TS2: Cancel branch must early-return (no merge)"
# Reset both buffers from snapshots.
assert re.search(
    r'this\.state\.feature\s*=\s*JSON\.parse\(\s*this\.state\.snapshotJson\s*\)',
    sw,
), "TS2: OK branch must reset state.feature from JSON.parse(snapshotJson)"
assert re.search(
    r'this\.state\.raw\s*=\s*this\.state\.snapshotRaw', sw
), "TS2: OK branch must reset state.raw from snapshotRaw"
assert re.search(r'this\.markDirty\(\s*false\s*\)', sw), (
    "TS2: OK branch must call markDirty(false) after reset"
)
assert "this.renderStructured()" in sw and "this.renderRaw()" in sw, (
    "TS2: OK branch must re-render both tabs"
)


# --- TS3: save() dispatches to saveRaw() when state.tab === 'raw'. ---
# Disambiguate from run-editor save() by requiring /api/files/ in body.
save = _body(r"async\s+save\s*\(\s*\)", contains="/api/files/")
assert re.search(
    r'if\s*\(\s*this\.state\.tab\s*===?\s*"raw"\s*\)\s*return\s+this\.saveRaw\(\s*\)',
    save,
), "TS3: save() must early-return this.saveRaw() when state.tab === 'raw'"

print(
    "PASS  TS1 + TS2 + TS3: switchTab no-op on same target, dirty-buffer confirm + "
    "snapshot reset, save() dispatches to saveRaw() on raw tab"
)
