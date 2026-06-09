# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / AC3 -- structured save drops empty steps silently.

End-to-end of the full save flow:
  1. Server REJECTS the uncleaned payload (`validation_error` on the
     empty-text step). This proves cleanup is REQUIRED, not optional.
  2. The client-side `cleanupBuffer` body (asserted statically in
     F08_12) drops empty-text steps; mirror that policy in Python.
  3. PATCH the cleaned payload -> 200; on-disk reflects only the
     non-empty steps. From the user's POV the empty step is dropped
     silently and the save succeeds, matching the AC.
"""
import pathlib
import tempfile

from app import create_app


def cleanup_steps(steps: list[dict]) -> list[dict]:
    """Python mirror of `tmsEditor.cleanupBuffer` step filter."""
    return [s for s in steps if (s.get("text") or "").strip() != ""]


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "seed"},
    )

    # Buffer the user would have on screen: mix of empty + non-empty steps.
    base = client.get("/api/files/Alpha/Mod/case.feature").get_json()
    base["scenario"]["steps"] = [
        {"keyword": "Given", "text": "a real step", "data_table": None},
        {"keyword": "When", "text": "", "data_table": None},
        {"keyword": "Then", "text": "another real step", "data_table": None},
    ]
    base["background"]["steps"] = [
        {"keyword": "Given", "text": "  ", "data_table": None},
        {"keyword": "Given", "text": "background step", "data_table": None},
    ]

    # --- (1) Server REJECTS uncleaned payload. ---
    uncleaned = {
        **base,
        "background": {"steps": list(base["background"]["steps"])},
        "scenario": {**base["scenario"], "steps": list(base["scenario"]["steps"])},
    }
    r = client.patch("/api/files/Alpha/Mod/case.feature", json=uncleaned)
    assert r.status_code == 422, (
        f"AC3 (precondition): server must REJECT empty-text steps with 422; "
        f"got {r.status_code}. If the server ever starts cleaning silently, this "
        f"smoke is no longer testing the client's cleanupBuffer responsibility."
    )

    # --- (2) Client-side cleanup, mirroring tmsEditor.cleanupBuffer. ---
    cleaned = {
        **base,
        "background": {**base["background"], "steps": cleanup_steps(base["background"]["steps"])},
        "scenario": {**base["scenario"], "steps": cleanup_steps(base["scenario"]["steps"])},
    }

    # --- (3) PATCH cleaned payload -> 200; disk reflects only real steps. ---
    r = client.patch("/api/files/Alpha/Mod/case.feature", json=cleaned)
    assert r.status_code == 200, (
        f"AC3: PATCH with cleaned payload must succeed; "
        f"got {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    after = client.get("/api/files/Alpha/Mod/case.feature").get_json()
    bg_texts = [s["text"] for s in after["background"]["steps"]]
    sc_texts = [s["text"] for s in after["scenario"]["steps"]]
    assert bg_texts == ["background step"], (
        f"AC3: only the non-empty background step must survive; got {bg_texts!r}"
    )
    assert sc_texts == ["a real step", "another real step"], (
        f"AC3: only non-empty scenario steps must survive; got {sc_texts!r}"
    )

print("PASS  AC3: server rejects uncleaned payload; client-cleaned save succeeds and the empty step is dropped silently on disk")
