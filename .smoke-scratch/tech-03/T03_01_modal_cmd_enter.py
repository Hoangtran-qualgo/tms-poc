# Pattern: see .smoke-scratch/README.md
"""tech-03 / shared modal -- Cmd+Return confirms the primary action.

Every in-app create / update / add modal is built by the single
`tmsOpenModal` primitive, so adding the keyboard shortcut once there makes
all of them inherit it. This pins:

  K1: a single shared `triggerConfirm` path used by BOTH the Confirm
      button click and the keyboard shortcut.
  K2: `triggerConfirm` respects the disabled gate, the no-confirm
      (information-only) modals, and an in-flight guard (no double-submit).
  K3: the modal `keydown` handler fires the confirm on Cmd+Return
      (metaKey + Enter) with preventDefault, and still closes on Escape.

Static JS inspection of app/static/03_folder_actions.js.
"""
import re
import pathlib

JS = pathlib.Path("app/static/03_folder_actions.js").read_text()

# `triggerConfirm` and `onKey` are unique to tmsOpenModal in this file.

# --- K1: one shared confirm path, used by the button click. ---
assert "const triggerConfirm = async () =>" in JS, "shared triggerConfirm missing"
assert 'confirmBtn.addEventListener("click", triggerConfirm)' in JS, (
    "Confirm button must reuse the shared triggerConfirm (not a separate handler)"
)

# --- K2: disabled / no-confirm / in-flight guards. ---
guard = re.search(r"const triggerConfirm = async \(\) =>\s*\{.*?\n  \};", JS, re.DOTALL)
assert guard, "triggerConfirm body not found"
guard = guard.group(0)
assert "!hasConfirm" in guard, "info-only modals (no Confirm) must not trigger"
assert "confirmBtn.disabled" in guard, "disabled gate must be respected"
assert "confirmInFlight" in guard, "in-flight guard missing (would allow double-submit)"
assert "await onConfirm?.({ close })" in guard, "must invoke the caller's onConfirm"

# --- K3: keydown handler — Cmd+Return confirms, Escape still closes. ---
onkey = re.search(r"const onKey = \(e\) =>\s*\{.*?\n  \};", JS, re.DOTALL)
assert onkey, "onKey handler not found"
onkey = onkey.group(0)
assert 'e.key === "Escape"' in onkey and "close()" in onkey, "Escape-to-close regressed"
assert 'e.metaKey && e.key === "Enter"' in onkey, "Cmd+Return shortcut missing"
assert "e.preventDefault()" in onkey, "Cmd+Return must preventDefault"
assert "triggerConfirm()" in onkey, "Cmd+Return must route through the shared confirm path"

print("PASS  K1+K2+K3: Cmd+Return confirms via the shared, guarded modal path; Escape still closes")
