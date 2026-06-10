# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / SS2 + SS3 + SS4 + SS5 + SS6 -- structured save.

Static inspection of `tmsEditor.save()` and `_refreshFromDisk()`:

SS2: cleanupBuffer is called; on error, alert("Cannot save: ...") + abort.
SS3: after cleanup, save re-renders steps + examples BEFORE the PATCH.
SS4: PATCH /api/files/<state.path> with JSON.stringify(state.feature).
SS5: 2xx -> await _refreshFromDisk() (refetches both endpoints + resets
     snapshots + markDirty(false) + re-renders) then flashSaved().
SS6: non-2xx -> alert("Save failed: ...") + buffer stays dirty.

Cross-credit (SS4): feature-05/F05_02_ui_triggers.py UI4 already asserts
the PATCH endpoint + body shape. This smoke owns the controller-flow
ordering claims (SS2/SS3/SS5/SS6 + the cleanup gate).
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


SAVE = _body(r"async\s+save\s*\(\s*\)", contains="cleanupBuffer")


# --- SS2: cleanupBuffer + alert("Cannot save: ...") + abort. ---
assert re.search(
    r'const\s+err\s*=\s*this\.cleanupBuffer\(\s*\)', SAVE
), "SS2: save() must call this.cleanupBuffer() and capture the result"
assert re.search(
    r'if\s*\(\s*err\s*\)\s*\{[\s\S]{0,300}?alert\(\s*"Cannot save: "\s*\+\s*err\s*\)',
    SAVE,
), "SS2: save() must alert('Cannot save: ' + err) when cleanupBuffer returns a message"
# The error branch returns BEFORE the PATCH so no network call is made.
err_branch = re.search(
    r'if\s*\(\s*err\s*\)\s*\{([\s\S]+?)\}', SAVE
).group(1)
assert "return" in err_branch and "fetch(" not in err_branch, (
    "SS2: cleanupBuffer-error branch must return WITHOUT issuing a fetch"
)


# --- SS3: re-render after cleanup, BEFORE the PATCH. ---
# Locate the slice from after cleanupBuffer to the fetch().
after_clean = SAVE[SAVE.index("cleanupBuffer"):]
patch_idx = after_clean.index('fetch("/api/files/')
pre_patch = after_clean[:patch_idx]
for fn in (
    'this.renderSteps("background"',
    'this.renderSteps("scenario"',
    "this.renderExamplesSection()",
):
    assert fn in pre_patch, (
        f"SS3: save() must call {fn} BETWEEN cleanupBuffer and the PATCH fetch"
    )


# --- SS4: PATCH /api/files/<state.path> with JSON.stringify(state.feature). ---
assert re.search(
    r'fetch\(\s*"/api/files/"\s*\+\s*this\.state\.path\s*,\s*\{[\s\S]{0,200}?method:\s*"PATCH"',
    SAVE,
), "SS4: save() must PATCH /api/files/<state.path>"
assert "JSON.stringify(this.state.feature)" in SAVE, (
    "SS4: save() PATCH body must be JSON.stringify(this.state.feature)"
)
assert '"Content-Type": "application/json"' in SAVE, (
    "SS4: save() PATCH must declare Content-Type: application/json"
)


# --- SS5: 2xx branch -- await _refreshFromDisk() then flashSaved(). ---
# Match the 2xx ordering: refresh comes before flashSaved.
assert re.search(
    r'await\s+this\._refreshFromDisk\(\s*\)\s*;\s*this\.flashSaved\(\s*\)',
    SAVE,
), "SS5: save() 2xx branch must `await this._refreshFromDisk(); this.flashSaved();` in order"

# _refreshFromDisk body shape.
REF = _body(r"async\s+_refreshFromDisk\s*\(\s*\)")
assert re.search(
    r'fetch\(\s*"/api/files/"\s*\+\s*this\.state\.path\s*\)', REF
), "SS5: _refreshFromDisk must refetch /api/files/<p>"
assert re.search(
    r'fetch\(\s*"/api/files/"\s*\+\s*this\.state\.path\s*\+\s*"/raw"\s*\)', REF
), "SS5: _refreshFromDisk must refetch /api/files/<p>/raw"
for line in (
    "this.state.feature = feature",
    "this.state.raw = raw",
    "this.state.snapshotJson = JSON.stringify(feature)",
    "this.state.snapshotRaw = raw",
    "this.markDirty(false)",
    "this.renderStructured()",
    "this.renderRaw()",
):
    assert line in REF, (
        f"SS5: _refreshFromDisk must include `{line}` "
        "(state mirror + snapshots reset + markDirty(false) + re-render both tabs)"
    )


# --- SS6: non-2xx branch -- alert('Save failed: ...') + no markDirty(false). ---
assert re.search(
    r'if\s*\(\s*!\s*r\.ok\s*\)\s*\{[\s\S]{0,200}?alert\(\s*"Save failed: "\s*\+',
    SAVE,
), "SS6: save() non-2xx branch must alert('Save failed: ' + ...)"
# Non-2xx branch must NOT call _refreshFromDisk or markDirty(false).
nonok_branch = re.search(
    r'if\s*\(\s*!\s*r\.ok\s*\)\s*\{([\s\S]+?)\}\s*//.*?canonicalised', SAVE
)
# Fallback split: take from `if (!r.ok) {` to the matching `}`.
m_nonok = re.search(r'if\s*\(\s*!\s*r\.ok\s*\)\s*\{', SAVE)
assert m_nonok, "SS6: save() must have non-2xx branch `if (!r.ok) { ... }`"
i = m_nonok.end() - 1
depth = 0
for j in range(i, len(SAVE)):
    c = SAVE[j]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            nonok = SAVE[i:j + 1]
            break
assert "_refreshFromDisk" not in nonok, (
    "SS6: non-2xx branch must NOT call _refreshFromDisk (buffer stays dirty)"
)
assert "markDirty(false)" not in nonok, (
    "SS6: non-2xx branch must NOT call markDirty(false) (buffer stays dirty)"
)
assert "return" in nonok, (
    "SS6: non-2xx branch must early-return after the alert"
)

print(
    "PASS  SS2 + SS3 + SS4 + SS5 + SS6: cleanup gate + re-render before PATCH + "
    "PATCH /api/files/<p> JSON-body + 2xx refresh+flashSaved + non-2xx alert keeps "
    "buffer dirty"
)
