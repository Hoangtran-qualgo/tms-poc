# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Atomicity & locking (AL1).

Per Step-1 sign-off decision (b): proves the route layer invokes
`Storage._mark_write` for every mutation by snapshotting
`s._recent_writes` immediately after each call and asserting the
target paths are present.

Underlying primitives (`_atomic_write_bytes`, `_mark_write`,
`was_recently_written`) are primary-framed in feature-02
(F02_03_atomic_write.py, F02_06_self_write.py) and feature-03
(F03_01_event_filtering.py); this smoke is the route-layer
integration proof.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod2"})

    mod_dir = root / "Alpha" / "Mod"
    mod2_dir = root / "Alpha" / "Mod2"

    def _snapshot() -> set[str]:
        # Snapshot the keys under the lock to avoid racing the
        # opportunistic cleanup in _mark_write.
        with s._recent_writes_lock:
            return set(s._recent_writes.keys())

    # --- AL1 for POST /api/files (create_file) -----------------------------
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "f1", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 201, "AL1 setup: create must succeed"
    target = str(mod_dir / "f1.feature")
    snap = _snapshot()
    assert target in snap, (
        f"AL1[POST /api/files]: target {target!r} must be in _recent_writes after create; "
        f"snap={sorted(snap)}"
    )
    assert str(mod_dir) in snap, (
        f"AL1[POST /api/files]: parent dir {str(mod_dir)!r} must be in _recent_writes after create"
    )

    # --- AL1 for PATCH /api/files/<p> (write_feature) ----------------------
    existing = client.get("/api/files/Alpha/Mod/f1.feature").get_json()
    existing["description"] = "edited"
    r = client.patch("/api/files/Alpha/Mod/f1.feature", json=existing)
    assert r.status_code == 200, "AL1 setup: PATCH must succeed"
    snap = _snapshot()
    assert target in snap, (
        f"AL1[PATCH /api/files/<p>]: target {target!r} must be in _recent_writes after PATCH"
    )

    # --- AL1 for PUT /api/files/<p>/raw (write_raw) ------------------------
    new_raw = "Feature: rewritten\n  desc\n\n  Scenario: s\n    Given a step\n"
    r = client.put(
        "/api/files/Alpha/Mod/f1.feature/raw",
        data=new_raw.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 200, "AL1 setup: PUT raw must succeed"
    snap = _snapshot()
    assert target in snap, (
        f"AL1[PUT /api/files/<p>/raw]: target {target!r} must be in _recent_writes after PUT raw"
    )

    # --- AL1 for PATCH /api/files/<p>/rename (rename_file) -----------------
    r = client.patch(
        "/api/files/Alpha/Mod/f1.feature/rename",
        json={"file_name": "renamed"},
    )
    assert r.status_code == 200, "AL1 setup: rename must succeed"
    src = str(mod_dir / "f1.feature")
    dst = str(mod_dir / "renamed.feature")
    snap = _snapshot()
    assert src in snap, (
        f"AL1[rename]: source {src!r} must be in _recent_writes (so the watcher "
        f"suppresses the source-side FS event)"
    )
    assert dst in snap, (
        f"AL1[rename]: destination {dst!r} must be in _recent_writes (so the "
        f"watcher suppresses the destination-side FS event)"
    )

    # --- AL1 for PATCH /api/files/<p>/move (move_file) ---------------------
    r = client.patch(
        "/api/files/Alpha/Mod/renamed.feature/move",
        json={"parent": "Alpha/Mod2"},
    )
    assert r.status_code == 200, "AL1 setup: move must succeed"
    src = str(mod_dir / "renamed.feature")
    dst = str(mod2_dir / "renamed.feature")
    snap = _snapshot()
    assert src in snap, f"AL1[move]: source {src!r} must be in _recent_writes"
    assert dst in snap, f"AL1[move]: destination {dst!r} must be in _recent_writes"
    # Both parent dirs marked too (mark_write also tags the parent).
    assert str(mod_dir) in snap, (
        f"AL1[move]: source parent {str(mod_dir)!r} must be in _recent_writes"
    )
    assert str(mod2_dir) in snap, (
        f"AL1[move]: destination parent {str(mod2_dir)!r} must be in _recent_writes"
    )

    # --- AL1 for POST /api/files/<p>/duplicate (duplicate_file) ------------
    r = client.post(
        "/api/files/Alpha/Mod2/renamed.feature/duplicate",
        json={"file_name": "copy"},
    )
    assert r.status_code == 201, "AL1 setup: duplicate must succeed"
    dup_target = str(mod2_dir / "copy.feature")
    snap = _snapshot()
    assert dup_target in snap, (
        f"AL1[duplicate]: copy target {dup_target!r} must be in _recent_writes"
    )

    # --- AL1 for DELETE /api/files/<p> (delete_file) -----------------------
    r = client.delete("/api/files/Alpha/Mod2/copy.feature")
    assert r.status_code == 204, "AL1 setup: DELETE must succeed"
    snap = _snapshot()
    assert dup_target in snap, (
        f"AL1[DELETE]: deleted target {dup_target!r} must be in _recent_writes "
        f"(so a delayed FS event for the deletion is suppressed)"
    )
    assert str(mod2_dir) in snap, (
        f"AL1[DELETE]: parent dir {str(mod2_dir)!r} must be in _recent_writes "
        f"(spec: 'covers both target and parent dir')"
    )
print(
    "PASS  AL1: every file-CRUD route mutation marks the target (and parent dir / "
    "secondary path) in Storage._recent_writes -> the watcher's was_recently_written "
    "filter will suppress the resulting FS events"
)
