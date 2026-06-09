# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / DM6 -- created_at server-stamped + immutable.

DM6: created_at is stamped server-side in UTC ISO-8601 form
     (timespec=seconds) at create; clients cannot override it; Save
     round-trips the stored value verbatim.

- create via POST /api/runs with a bogus client-supplied created_at in
  the body -> the stored value is the server stamp, NOT the client's.
- the stamp is UTC, seconds-precision (no microseconds, has +00:00).
- a PATCH that supplies the stored created_at round-trips it verbatim.
"""
import json
import datetime as dt
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    client = app.test_client()

    # --- DM6: client-supplied created_at is ignored (server stamps). ---
    bogus = "1999-01-01T00:00:00+00:00"
    r = client.post("/api/runs", data=json.dumps({
        "project": "Alpha", "group": "release-1", "name": "Smoke",
        "file_name": "smoke", "case_paths": [], "created_at": bogus,
    }), content_type="application/json")
    assert r.status_code == 201, r.get_data(as_text=True)

    stamped = s.read_run("Alpha", "release-1", "smoke.yaml").created_at
    assert stamped != bogus, "client must not be able to override created_at"

    # --- DM6: UTC, seconds precision (parseable, +00:00, no microseconds). ---
    parsed = dt.datetime.fromisoformat(stamped)
    assert parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0), stamped
    assert parsed.microsecond == 0, f"created_at must be seconds-precision, got {stamped}"

    # --- DM6: Save round-trips created_at verbatim. ---
    r2 = client.patch("/api/runs/Alpha/release-1/smoke.yaml", data=json.dumps({
        "name": "Smoke 2", "created_at": stamped, "description": "x", "results": [],
    }), content_type="application/json")
    assert r2.status_code == 200, r2.get_data(as_text=True)
    assert s.read_run("Alpha", "release-1", "smoke.yaml").created_at == stamped, (
        "Save must preserve created_at verbatim"
    )

print("PASS  DM6: created_at is server-stamped UTC/seconds, client cannot override, round-trips verbatim on Save")
