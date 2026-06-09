# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / ST1 + SF4 -- error mapping.

ST1: an invalid `match` mode (not in {text,tag}) makes Storage.search
     raise ValueError → API maps to HTTP 400 (`bad_request` envelope).
SF4: malformed `scope` syntax raises ValueError → HTTP 400 on the API
     and an inline 400 snippet on the UI route.

Cross-credit: feature-02/F02_07 exercises the raw ValueError at the
storage layer; this smoke owns the route-level 400 mapping.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "hit.feature"], "needle here")

    # --- ST1: invalid match mode → 400 (API). ---
    r = client.get("/api/search?q=needle&match=bogus")
    assert r.status_code == 400, (
        f"ST1: invalid match mode must return HTTP 400, got {r.status_code}"
    )
    env = r.get_json()
    assert env["error"]["code"] == "bad_request", (
        f"ST1: invalid match must produce a 'bad_request' envelope, got {env!r}"
    )

    # --- SF4: malformed scope → 400 (API). ---
    # `project:` with no name is invalid per _scope_to_segments.
    for bad_scope in ("project:", "project:a/b", "module:onlyone", "module:a/b/c", "garbage"):
        r = client.get(f"/api/search?q=needle&scope={bad_scope}")
        assert r.status_code == 400, (
            f"SF4: malformed scope {bad_scope!r} must return HTTP 400 at /api/search, "
            f"got {r.status_code}"
        )
        assert r.get_json()["error"]["code"] == "bad_request", (
            f"SF4: scope {bad_scope!r} must produce a 'bad_request' envelope"
        )

    # --- SF4: malformed scope → inline 400 (UI). ---
    # q must be non-empty so /ui/search reaches Storage.search (it strips
    # + short-circuits on blank q before any scope parsing).
    r = client.get("/ui/search?q=needle&scope=project:")
    assert r.status_code == 400, (
        f"SF4: malformed scope must return HTTP 400 at /ui/search, got {r.status_code}"
    )

    # --- A VALID scope must NOT 400 (guards against over-broad rejection). ---
    ok = client.get("/api/search?q=needle&scope=project:Alpha")
    assert ok.status_code == 200, (
        f"SF4: a valid scope must return 200, got {ok.status_code}"
    )

print("PASS  ST1 + SF4: invalid match → 400; malformed scope → 400 on /api/search and inline 400 on /ui/search; valid scope → 200")
