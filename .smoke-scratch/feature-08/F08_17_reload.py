# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / RL1 + RL2 + RL3 + RL4 -- reload.

Static inspection of tmsEditor.reload() body:
  RL1: dirty-buffer confirm with the spec literal.
  RL2: calls _refreshFromDisk() (shared with post-save reload).
  RL3: clears banner, raw error, lingering Saved badge.
  RL4: failure surfaces via alert('Reload failed: ...').
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Locate file-editor reload() body. ---
BODY = None
for m in re.finditer(r"async\s+reload\s*\(\s*\)\s*\{", JS):
    start = m.end() - 1
    depth = 0
    for i in range(start, len(JS)):
        c = JS[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                cand = JS[start:i + 1]
                if "_refreshFromDisk" in cand:
                    BODY = cand
                break
    if BODY:
        break
assert BODY, "RL-suite: tmsEditor.reload() body must exist"


# --- RL1: dirty confirm with the spec literal. ---
assert re.search(
    r'this\.state\.dirty\s*&&[\s\S]{0,80}?window\.confirm\(\s*"Discard unsaved changes and reload from disk\?"',
    BODY,
), "RL1: reload() must confirm with the spec literal when state.dirty"
# Cancel branch: early-return.
assert re.search(r'\)\s*\)\s*return', BODY), (
    "RL1: reload() must early-return when the user cancels the confirm"
)


# --- RL2: calls _refreshFromDisk() (shared post-save reload). ---
assert re.search(
    r'await\s+this\._refreshFromDisk\(\s*\)', BODY
), "RL2: reload() must await this._refreshFromDisk()"


# --- RL3: clears banner, raw error, lingering Saved badge. ---
assert "this._hideBanner()" in BODY, (
    "RL3: reload() must call this._hideBanner() to clear any banner"
)
assert "this.hideRawError()" in BODY, (
    "RL3: reload() must call this.hideRawError() to clear the raw error region"
)
assert "this._hideSavedBadge()" in BODY, (
    "RL3: reload() must call this._hideSavedBadge() to clear any lingering Saved badge"
)


# --- RL4: failure surfaces via alert('Reload failed: ...'). ---
assert re.search(
    r'catch\s*\(\s*e\s*\)\s*\{[\s\S]{0,80}?alert\(\s*"Reload failed: "\s*\+\s*e\.message',
    BODY,
), "RL4: reload() catch branch must alert('Reload failed: ' + e.message)"

print("PASS  RL1 + RL2 + RL3 + RL4: reload() dirty-confirm; _refreshFromDisk; clears banner+raw-error+Saved; catch alerts on failure")
