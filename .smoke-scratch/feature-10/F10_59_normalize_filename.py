# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM15 -- _normalize_run_filename.

SM15: _normalize_run_filename(name) auto-appends `.yaml` when the name
     has no extension, returns it unchanged when it already ends in
     `.yaml` (case-insensitive), and rejects any other extension (or an
     empty name) with ValueError.
"""
from app.storage import _normalize_run_filename

# --- SM15: no extension -> .yaml appended. ---
assert _normalize_run_filename("sprint-1") == "sprint-1.yaml"

# --- SM15: already .yaml -> returned verbatim (case-insensitive match). ---
assert _normalize_run_filename("sprint-1.yaml") == "sprint-1.yaml"
assert _normalize_run_filename("Sprint.YAML") == "Sprint.YAML"

# --- SM15: a different extension -> ValueError. ---
for bad in ["run.yml", "run.txt", "run.feature"]:
    try:
        _normalize_run_filename(bad)
        raise AssertionError(f"{bad!r} must be rejected (only .yaml allowed)")
    except ValueError:
        pass

# --- SM15: empty name -> ValueError. ---
try:
    _normalize_run_filename("")
    raise AssertionError("empty name must raise ValueError")
except ValueError:
    pass

print("PASS  SM15: _normalize_run_filename appends .yaml, accepts .yaml verbatim, rejects other extensions + empty")
