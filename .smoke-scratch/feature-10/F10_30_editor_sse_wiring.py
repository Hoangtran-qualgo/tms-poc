"""3.G — SSE external-change wiring smoke.

Live SSE in two tabs needs a browser (per the Phase-2 lock-in). This
script verifies the static artefacts the listener depends on:

  - tmsRunEditor exposes onExternalChange + banner methods.
  - The body-level `sse:change` handler now fans out to the run
    editor in addition to the file editor.
  - The template carries the banner placeholder (#run-editor-banner)
    the controller targets.
  - `_reloadAndAnnounce` queues a pending banner that survives the
    htmx.ajax swap (via the tmsRunEditor._pendingBanner sentinel
    picked up in boot()).
"""
import pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))
TPL = pathlib.Path("app/templates/run_editor.html").read_text()

# Controller surface.
for sym in [
    "async onExternalChange()",
    "_reloadAndAnnounce(",
    "_navigateToGroup()",
    "_showBanner(",
    "_hideBanner()",
    "_pendingBanner",
]:
    assert sym in APP_JS, f"missing JS symbol: {sym}"
print("PASS 3.G controller exposes onExternalChange + banner surface")

# Banner element exists in the template.
assert 'id="run-editor-banner"' in TPL, "#run-editor-banner placeholder missing"
print("PASS 3.G template carries the #run-editor-banner placeholder")

# Body-level sse:change handler covers BOTH editors.
sse_block_re = APP_JS.find('document.body.addEventListener("sse:change"')
assert sse_block_re != -1, "no body-level sse:change handler"
sse_block = APP_JS[sse_block_re:sse_block_re + 400]
assert "tmsEditor.onExternalChange()" in sse_block, "file editor still wired"
assert "tmsRunEditor.onExternalChange()" in sse_block, "run editor not fanned out"
print("PASS 3.G sse:change handler fans out to both editors")

# Reload uses the partial route so server recomputes tombstones.
assert (
    "/ui/run/${project}/${group}/${file_name}" in APP_JS
), "external-reload should target the UI partial, not the JSON API"
print("PASS 3.G external-reload re-renders via /ui/run (server recomputes tombstones)")

# Discard action navigates to the group view (so the user lands on
# their group, not the global root).
assert "/ui/folder/${project}/test-run/${group}" in APP_JS, "Discard target wrong"
print("PASS 3.G removed-on-disk Discard action lands on the group view")

# Pending banner is consumed inside boot() so it survives the htmx swap.
boot_idx = APP_JS.find("boot() {")
assert boot_idx != -1
# Find the matching close-brace by counting depth.
depth = 0
i = boot_idx + len("boot() {")
boot_end = -1
while i < len(APP_JS):
    c = APP_JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        if depth == 0:
            boot_end = i
            break
        depth -= 1
    i += 1
assert boot_end != -1, "couldn't find end of boot()"
boot_body = APP_JS[boot_idx:boot_end]
assert "_pendingBanner" in boot_body, "boot() should consume _pendingBanner"
print("PASS 3.G boot() consumes the deferred banner queued before re-mount")
