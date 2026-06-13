# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / RT1 + MS3 (API half).

RT1: `GET /api/search` accepts q/scope/match/case query args and returns
     JSON `{ "hits": [SearchHit, ...] }`. `case` is truthy for
     {true,1,yes} (case-insensitive), falsy otherwise.
MS3: an empty `q` at the API returns `{ "hits": [] }` (the route does
     NOT strip; it delegates to Storage.search which returns []).

Re-owns the storage hit envelope end-to-end through the JSON route
(cross-credit: feature-02/F02_07_search.py exercises Storage.search
directly).
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
    # Description uses uppercase NEEDLE so the case param's effect is visible.
    s.create_file(["Alpha", "Mod", "hit.feature"], "contains NEEDLE here")

    # --- RT1: envelope shape + 200. ---
    r = client.get("/api/search?q=NEEDLE&scope=all&match=text&case=false")
    assert r.status_code == 200, f"RT1: /api/search must return 200, got {r.status_code}"
    body = r.get_json()
    assert isinstance(body, dict) and "hits" in body, (
        f"RT1: response must be a JSON object with a 'hits' key, got {body!r}"
    )
    assert isinstance(body["hits"], list), "RT1: 'hits' must be a list"
    assert len(body["hits"]) == 1, f"RT1: expected 1 hit, got {body['hits']!r}"
    hit = body["hits"][0]
    assert set(hit) == {"file_path", "description", "scenario_name", "matched_field", "match_value"}, (
        f"RT1: hit keys must be the SearchHit shape, got {set(hit)}"
    )
    assert hit["file_path"] == "Alpha/Mod/hit.feature", (
        f"RT1: file_path must be the relative posix path, got {hit['file_path']!r}"
    )

    # --- RT1: `case` param is parsed and forwarded (truthy variants). ---
    # Lowercase query vs uppercase description: case-insensitive hits,
    # case-sensitive misses. Proves the param flows to Storage.search.
    insensitive = client.get("/api/search?q=needle&match=text&case=false").get_json()
    assert len(insensitive["hits"]) == 1, (
        f"RT1: case=false must match case-insensitively, got {insensitive['hits']!r}"
    )
    for truthy in ("true", "1", "yes", "TRUE", "Yes"):
        sensitive = client.get(f"/api/search?q=needle&match=text&case={truthy}").get_json()
        assert sensitive["hits"] == [], (
            f"RT1: case={truthy!r} must be truthy (case-sensitive) → 0 hits for "
            f"'needle' vs 'NEEDLE', got {sensitive['hits']!r}"
        )
    # A non-truthy case value falls back to insensitive.
    falsy = client.get("/api/search?q=needle&match=text&case=nope").get_json()
    assert len(falsy["hits"]) == 1, (
        f"RT1: case='nope' is not truthy → insensitive → 1 hit, got {falsy['hits']!r}"
    )

    # --- MS3 (API half): empty q → {"hits": []}, no strip, no error. ---
    empty = client.get("/api/search?q=&match=text")
    assert empty.status_code == 200, "MS3: empty q must still be 200 at the API"
    assert empty.get_json() == {"hits": []}, (
        f"MS3: empty q at /api/search must return {{'hits': []}}, got {empty.get_json()!r}"
    )
    # Defaults: omitting scope/match/case entirely still works (scope=all, match=text).
    defaulted = client.get("/api/search?q=NEEDLE")
    assert defaulted.status_code == 200 and len(defaulted.get_json()["hits"]) == 1, (
        "RT1: omitting scope/match/case must default to scope=all/match=text"
    )

print("PASS  RT1 + MS3(API): /api/search returns {hits:[SearchHit]}, parses case truthy {true,1,yes}, empty q → {hits:[]}")
