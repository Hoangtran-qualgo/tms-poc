# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / RE5 + RE13 -- reload flow.

RE5: reload() confirms first when the buffer is dirty
     ("Reload from disk? Your unsaved changes will be discarded.")
     and on OK re-renders via htmx.ajax GET /ui/run/... into #main-pane.
RE13: the reload path goes through the UI partial (/ui/run/...), NOT
     the JSON API, so the server re-runs the per-row is_file() storm
     and tombstone state is always live. Both reload() and the
     external-change _reloadAndAnnounce() use the same /ui/run route.

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

m = re.search(r"async reload\(\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "tmsRunEditor.reload() must be defined"
reload_fn = m.group(0)

# --- RE5: dirty-guarded confirm with the exact copy. ---
assert re.search(r"if\s*\(\s*this\.state\.dirty\s*\)", reload_fn)
assert "Reload from disk? Your unsaved changes will be discarded." in reload_fn
assert "window.confirm(" in reload_fn
assert re.search(r"if\s*\(\s*!ok\s*\)\s*return", reload_fn), "must bail when confirm is cancelled"

# --- RE5 + RE13: re-render through the UI partial into #main-pane. ---
assert re.search(
    r'htmx\.ajax\(\s*"GET"\s*,\s*`/ui/run/\$\{project\}/\$\{group\}/\$\{file_name\}`',
    reload_fn,
), "reload() must htmx.ajax GET the /ui/run partial"
assert re.search(r'target:\s*"#main-pane"', reload_fn)

# --- RE13: the deferred-reload path also targets /ui/run (not the JSON API). ---
m2 = re.search(r"_reloadAndAnnounce\(kind, message\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m2, "_reloadAndAnnounce must be defined"
assert "/ui/run/${project}/${group}/${file_name}" in m2.group(0), (
    "RE13: external-change reload must also go through the /ui/run partial"
)

print("PASS  RE5+RE13: reload() confirms-if-dirty + re-renders via /ui/run partial into #main-pane (live tombstones)")
