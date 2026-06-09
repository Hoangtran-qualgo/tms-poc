# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / EB1 + EB2 + EB3 + EB4 -- external-change banner.

Static inspection of tmsEditor.onExternalChange() body:
  EB1: removed branch -> red "removed" banner; Discard action only.
  EB2: clean-buffer change -> silent reload + info banner.
  EB3: dirty-buffer change -> amber warn banner with Reload + Keep editing.
  EB4: Save button is NOT explicitly disabled by onExternalChange.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


# --- Locate file-editor onExternalChange() body. ---
BODY = None
for m in re.finditer(r"async\s+onExternalChange\s*\(\s*\)\s*\{", JS):
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
                # File-editor body references /api/files/, run editor references /api/runs/.
                if "/api/files/" in cand:
                    BODY = cand
                break
    if BODY:
        break
assert BODY, "EB-suite: tmsEditor.onExternalChange() body must exist"


# --- EB1: removed branch -- red banner + Discard only. ---
m_rem = re.search(
    r'if\s*\(\s*removed\s*\)\s*\{[\s\S]+?\}\s*(?=const\s+diskJson)', BODY
)
assert m_rem, "EB1: onExternalChange must have a removed-branch block"
removed_branch = m_rem.group(0)
assert re.search(
    r'kind:\s*"error"', removed_branch
), "EB1: removed branch must show an `error` kind banner (red)"
assert '"This file was removed on disk."' in removed_branch, (
    "EB1: removed branch must include the spec literal "
    "'This file was removed on disk.'"
)
# Only Discard action, no Reload or Keep editing.
assert removed_branch.count('label: "Discard"') == 1, (
    "EB1: removed branch must include exactly one `Discard` action"
)
for forbidden in ('label: "Reload', 'label: "Keep editing"'):
    assert forbidden not in removed_branch, (
        f"EB1: removed branch must NOT include {forbidden!r} (Discard only)"
    )


# --- EB2: clean-buffer change -- info banner + silent reload. ---
# After the diskJson identity check returns, the body branches on `!this.state.dirty`.
m_clean = re.search(
    r'if\s*\(\s*!\s*this\.state\.dirty\s*\)\s*\{([\s\S]+?)\n\s{0,8}\}',
    BODY,
)
assert m_clean, "EB2: onExternalChange must have a !state.dirty branch"
clean_branch = m_clean.group(1)
# Snapshot replace + re-render.
for line in (
    "this.state.feature = diskFeature",
    "this.state.raw = diskRaw",
    "this.state.snapshotJson = diskJson",
    "this.state.snapshotRaw = diskRaw",
    "this.renderStructured()",
    "this.renderRaw()",
):
    assert line in clean_branch, (
        f"EB2: clean-buffer branch must include `{line}`"
    )
assert re.search(r'kind:\s*"info"', clean_branch), (
    "EB2: clean-buffer branch must show an `info` kind banner"
)
assert '"File was updated externally; the editor reloaded."' in clean_branch, (
    "EB2: clean-buffer banner message must be the spec literal"
)
assert 'label: "Dismiss"' in clean_branch, (
    "EB2: clean-buffer info banner must offer a Dismiss action"
)


# --- EB3: dirty-buffer change -- amber warn banner with two actions. ---
# Final _showBanner call in the body (after the clean branch returned).
m_warn_kind = re.search(r'kind:\s*"warn"', BODY)
assert m_warn_kind, "EB3: onExternalChange must include a warn-kind banner branch"
assert '"File changed externally while you have unsaved changes."' in BODY, (
    "EB3: dirty-buffer banner message must be the spec literal"
)
assert 'label: "Reload (discard mine)"' in BODY, (
    "EB3: dirty branch must offer a 'Reload (discard mine)' action"
)
assert 'label: "Keep editing"' in BODY, (
    "EB3: dirty branch must offer a 'Keep editing' action"
)
# Reload action resets snapshots + markDirty(false).
m_reload = re.search(
    r'label:\s*"Reload \(discard mine\)"[\s\S]+?action:\s*\(\s*\)\s*=>\s*\{([\s\S]+?)\}\s*,?\s*\}',
    BODY,
)
assert m_reload, "EB3: Reload action handler must exist"
reload_action = m_reload.group(1)
assert "this.markDirty(false)" in reload_action, (
    "EB3: Reload action must call markDirty(false) so the buffer becomes clean"
)


# --- EB4: onExternalChange does NOT touch #btn-save.disabled. ---
assert "btn-save" not in BODY, (
    "EB4: onExternalChange must NOT touch #btn-save (validation gates already enforce the effect)"
)

print("PASS  EB1 + EB2 + EB3 + EB4: removed=error+Discard; clean=info+silent reload; dirty=warn+Reload/Keep editing; onExternalChange never touches #btn-save")
