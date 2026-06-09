# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / D1 + D2 + D4 -- dirty tracking (static half).

D1: every editable widget calls `this.markDirty(true)` on change.
D2: `markDirty(d)` toggles #dirty-indicator + recomputes Save button
    enabled state + clears the Saved badge.
D4: `beforeunload` warns when the buffer is dirty.

D3 (Save disabled when description empty) is end-to-end and lives in
its sibling F08_10b smoke per the Step-1 sign-off split.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


# --- Isolate the tmsEditor object body. ---
m = re.search(r'const\s+tmsEditor\s*=\s*\{', JS)
assert m, "D-suite: const tmsEditor must exist"
start = m.end() - 1
depth = 0
for i in range(start, len(JS)):
    c = JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            EDITOR = JS[start:i + 1]
            break
else:
    raise AssertionError("D-suite: failed to locate end of tmsEditor object")


# --- D1: every editable widget calls this.markDirty(true). ---
# Spec lists: description, feature/scenario tag chips, background/scenario
# steps, examples, raw textarea, kind toggle. Count the call sites and
# require enough breadth so a single widget regression cannot mask the rule.
markdirty_calls = re.findall(r'this\.markDirty\(\s*true\s*\)', EDITOR)
assert len(markdirty_calls) >= 8, (
    f"D1: tmsEditor must contain >= 8 `this.markDirty(true)` call sites "
    f"(description, chips, steps, examples, raw textarea, kind, data-table, "
    f"enums); got {len(markdirty_calls)}"
)

# Per-widget spot checks anchored on nearby identifying tokens.
# Direct anchor -> markDirty(true) within a short span.
for ctx, hint in (
    ("feature-description", "description textarea -> markDirty(true)"),
    ("raw-text", "raw textarea -> markDirty(true)"),
):
    pat = re.compile(
        rf'getElementById\(\s*"{re.escape(ctx)}"\s*\)[\s\S]{{0,400}}?this\.markDirty\(\s*true\s*\)'
    )
    assert pat.search(EDITOR), f"D1: missing markDirty(true) wiring for {hint}"

# Kind toggle wires through `_setKind(kind)` (not directly to markDirty).
# Confirm both halves: the wire AND the _setKind body's markDirty call.
assert re.search(
    r'getElementById\(\s*"kind-scenario"\s*\)\.addEventListener\(\s*"change"\s*,\s*\(\s*\)\s*=>\s*this\._setKind\(\s*"scenario"\s*\)',
    EDITOR,
), "D1: #kind-scenario change must wire to this._setKind('scenario')"
m_sk = re.search(r'_setKind\s*\(\s*kind\s*\)\s*\{', EDITOR)
assert m_sk, "D1: tmsEditor._setKind(kind) must exist"
sk_start = m_sk.end() - 1
depth = 0
for i in range(sk_start, len(EDITOR)):
    c = EDITOR[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            SK_BODY = EDITOR[sk_start:i + 1]
            break
assert "this.markDirty(true)" in SK_BODY, (
    "D1: _setKind body must call this.markDirty(true) so the kind toggle marks dirty"
)

# Step keyword/text/remove handlers + chip-add path do not have a stable
# anchor element id (rendered dynamically), so the count assertion above
# carries those.


# --- D2: markDirty(d) body. ---
mb = re.search(r'\bmarkDirty\s*\(\s*d\s*\)\s*\{', EDITOR)
assert mb, "D2: tmsEditor.markDirty(d) method must exist"
b_start = mb.end() - 1
depth = 0
for i in range(b_start, len(EDITOR)):
    c = EDITOR[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            MD_BODY = EDITOR[b_start:i + 1]
            break

assert re.search(
    r'this\.state\.dirty\s*=\s*!!\s*d', MD_BODY
), "D2: markDirty must set `this.state.dirty = !!d`"
assert re.search(
    r'getElementById\(\s*"dirty-indicator"\s*\)\.classList\.toggle\(\s*"hidden"\s*,\s*!this\.state\.dirty\s*\)',
    MD_BODY,
), "D2: markDirty must toggle #dirty-indicator `hidden` class based on dirty state"
assert "this.updateSaveButton()" in MD_BODY, (
    "D2: markDirty must call this.updateSaveButton() to recompute Save enabled"
)
assert re.search(
    r'if\s*\(\s*this\.state\.dirty\s*\)\s*this\._hideSavedBadge\(\s*\)',
    MD_BODY,
), "D2: markDirty must clear the Saved badge when becoming dirty"


# --- D4: window.addEventListener('beforeunload', ...) warns when dirty. ---
# Lives outside the tmsEditor object (module-level wiring at bottom of file).
m_bu = re.search(
    r'window\.addEventListener\(\s*"beforeunload"\s*,\s*\(\s*e\s*\)\s*=>\s*\{',
    JS,
)
assert m_bu, "D4: window.addEventListener('beforeunload', ...) must exist"
b_start = m_bu.end() - 1
depth = 0
for i in range(b_start, len(JS)):
    c = JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            BU_BODY = JS[b_start:i + 1]
            break

assert "tmsEditor.state" in BU_BODY and "dirty" in BU_BODY, (
    "D4: beforeunload handler must consult tmsEditor.state.dirty"
)
assert "e.preventDefault()" in BU_BODY, (
    "D4: beforeunload handler must call e.preventDefault() to trigger the "
    "browser-native confirm"
)
assert 'e.returnValue = ""' in BU_BODY, (
    "D4: beforeunload handler must set e.returnValue to trigger legacy browsers"
)

print("PASS  D1 + D2 + D4: markDirty(true) wired to editable widgets; markDirty body toggles indicator + clears Saved; beforeunload warns when dirty")
