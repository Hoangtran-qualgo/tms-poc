# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / RE1 -- tmsRunEditor.boot() bootstrap.

RE1: boot() reads #run-editor.dataset (project/group/fileName/
     createdAt), captures baselineJson = JSON.stringify(_readCurrent()),
     wires input + header listeners, then consumes the deferred
     _pendingBanner sentinel if one was queued by a prior instance.
     With no #run-editor in the DOM it clears state and returns.

Static JS inspection of app/static/app.js (no runtime).
"""
import re
import pathlib

JS = pathlib.Path("app/static/app.js").read_text()

# Scope to the boot() body (from `boot() {` to `_readCurrent()`'s start).
m = re.search(r"\bboot\(\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "tmsRunEditor.boot() must be defined"
boot = m.group(0)

# --- RE1: no #run-editor -> clear state + bail. ---
assert 'getElementById("run-editor")' in boot
assert re.search(r"if\s*\(\s*!root\s*\)\s*\{\s*this\.state\s*=\s*null", boot)

# --- RE1: reads all four dataset fields. ---
for field in ["root.dataset.project", "root.dataset.group",
              "root.dataset.fileName", "root.dataset.createdAt"]:
    assert field in boot, f"boot() must read {field}"

# --- RE1: captures the baseline snapshot. ---
assert "this.state.baselineJson = JSON.stringify(this._readCurrent())" in boot

# --- RE1: wires inputs + header buttons + initial dirty refresh. ---
assert "this._wireInputs();" in boot
assert "this._wireHeaderButtons();" in boot
assert "this._refreshDirty();" in boot

# --- RE1: consumes the deferred pending banner. ---
assert re.search(r"if\s*\(\s*this\._pendingBanner\s*\)", boot)
assert "this._pendingBanner = null;" in boot

print("PASS  RE1: boot() reads dataset, captures baselineJson, wires listeners, consumes _pendingBanner")
