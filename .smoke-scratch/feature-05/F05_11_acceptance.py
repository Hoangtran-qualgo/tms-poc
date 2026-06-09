# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Acceptance criteria (AC1-AC7).

AC7 is split per Step-1 sign-off into:
- AC7a: API-route file mutation -> zero SSE events on the bus.
- AC7b: external file mutation -> exactly one SSE event per open tab
        after DEBOUNCE_SECONDS.
"""
import pathlib
import queue
import tempfile
import time

from app import create_app
from app.watcher import DEBOUNCE_SECONDS


# --- AC1: POST /api/files at depth-1 parent -> 400 -------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    r = client.post(
        "/api/files",
        json={"parent": "Alpha", "file_name": "case", "description": "x"},
    )
    assert r.status_code == 400, (
        f"AC1: file create at depth-1 parent (project only) must return 400, "
        f"got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request", (
        "AC1: depth-1 parent rejection must carry error.code='bad_request'"
    )
print("PASS  AC1: POST /api/files with depth-1 parent (project only) -> 400 bad_request")


# --- AC2: POST /api/files with name conflict -> 409 ------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "first"},
    )
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "second"},
    )
    assert r.status_code == 409, (
        f"AC2: name-conflicting POST must return 409, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "name_conflict", (
        "AC2: conflict must carry error.code='name_conflict'"
    )
print("PASS  AC2: POST /api/files with name conflict -> 409 name_conflict")


# --- AC3: structured PATCH + raw PUT after GET /raw -> byte-identical disk -
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
    target = root / "Alpha" / "Mod" / "case.feature"

    # Apply a structured PATCH first; capture the resulting on-disk bytes.
    body = client.get("/api/files/Alpha/Mod/case.feature").get_json()
    body["description"] = "edited via structured patch"
    r = client.patch("/api/files/Alpha/Mod/case.feature", json=body)
    assert r.status_code == 200, "AC3 setup: PATCH must succeed"
    bytes_after_patch = target.read_bytes()

    # GET /raw to capture the canonical raw text, then PUT it back via /raw.
    raw_text = client.get(
        "/api/files/Alpha/Mod/case.feature/raw"
    ).get_data(as_text=True)
    r = client.put(
        "/api/files/Alpha/Mod/case.feature/raw",
        data=raw_text.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 200, "AC3 setup: PUT raw must succeed"
    bytes_after_raw = target.read_bytes()

    assert bytes_after_patch == bytes_after_raw, (
        "AC3: structured PATCH and raw PUT (after GET /raw round-trip) must "
        "produce byte-identical files on disk; got\n"
        f"  patch ({len(bytes_after_patch)} bytes): {bytes_after_patch!r}\n"
        f"  raw   ({len(bytes_after_raw)} bytes): {bytes_after_raw!r}"
    )
print("PASS  AC3: structured PATCH + raw PUT (after GET /raw) -> byte-identical files on disk")


# --- AC4: rename to conflicting name in same parent -> 409, source preserved
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "source", "description": "src desc"},
    )
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "taken", "description": "taken desc"},
    )

    src_path = root / "Alpha" / "Mod" / "source.feature"
    src_bytes_before = src_path.read_bytes()

    r = client.patch(
        "/api/files/Alpha/Mod/source.feature/rename",
        json={"file_name": "taken"},  # collides with existing taken.feature
    )
    assert r.status_code == 409, (
        f"AC4: rename to taken name must return 409, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "name_conflict", (
        "AC4: rename collision must carry error.code='name_conflict'"
    )
    # Source file must be preserved on disk + byte-identical.
    assert src_path.is_file(), "AC4: source file must remain on disk after rejected rename"
    assert src_path.read_bytes() == src_bytes_before, (
        "AC4: source file content must be byte-identical after rejected rename"
    )
print("PASS  AC4: rename to conflicting name -> 409 name_conflict; source preserved byte-for-byte")


# --- AC5: move across folders -> leaf + content byte-for-byte --------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModB"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/ModA", "file_name": "case", "description": "moveme"},
    )
    src_path = root / "Alpha" / "ModA" / "case.feature"
    dst_path = root / "Alpha" / "ModB" / "case.feature"  # leaf preserved
    src_bytes = src_path.read_bytes()

    r = client.patch(
        "/api/files/Alpha/ModA/case.feature/move",
        json={"parent": "Alpha/ModB"},
    )
    assert r.status_code == 200, f"AC5: move must succeed, got {r.status_code}"

    # Leaf name preserved.
    assert dst_path.is_file(), (
        f"AC5: destination must carry the SAME leaf 'case.feature' at the new parent; "
        f"checked {dst_path}"
    )
    assert not src_path.exists(), "AC5: source path must be gone after move"

    # Content byte-for-byte.
    assert dst_path.read_bytes() == src_bytes, (
        "AC5: file content must survive the move byte-for-byte"
    )
print("PASS  AC5: move across folders preserves leaf name AND content byte-for-byte")


# --- AC6: DELETE already-missing file -> 204 (idempotent) ------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    r = client.delete("/api/files/Nope/Missing/ghost.feature")
    assert r.status_code == 204, (
        f"AC6: DELETE never-existed file must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "AC6: 204 body must be empty"
print("PASS  AC6: DELETE already-missing file -> 204 (idempotent)")


# --- AC7a: API file-mutation -> zero SSE events on the bus -----------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    bus = app.extensions["bus"]

    # Seed BEFORE subscribing so seeding events don't pollute the count.
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod2"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "seed"},
    )
    time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

    q = bus.subscribe()
    try:
        # Drain in-flight events from the seeding burst.
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                break

        # Exercise every file-CRUD route -- each must produce ZERO events
        # because storage's _mark_write covers the target + parent dir and
        # the watcher's was_recently_written filter drops the FS events.
        body = client.get("/api/files/Alpha/Mod/case.feature").get_json()
        body["description"] = "patched"
        assert client.patch("/api/files/Alpha/Mod/case.feature", json=body).status_code == 200
        assert client.put(
            "/api/files/Alpha/Mod/case.feature/raw",
            data=b"Feature: x\n  desc\n\n  Scenario: s\n    Given step\n",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        ).status_code == 200
        assert client.patch(
            "/api/files/Alpha/Mod/case.feature/rename",
            json={"file_name": "renamed"},
        ).status_code == 200
        assert client.patch(
            "/api/files/Alpha/Mod/renamed.feature/move",
            json={"parent": "Alpha/Mod2"},
        ).status_code == 200
        assert client.post(
            "/api/files/Alpha/Mod2/renamed.feature/duplicate",
            json={"file_name": "copy"},
        ).status_code == 201
        assert client.delete("/api/files/Alpha/Mod2/copy.feature").status_code == 204
        assert client.delete("/api/files/Alpha/Mod2/renamed.feature").status_code == 204

        # Wait well past DEBOUNCE_SECONDS plus FS-event slack.
        time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

        received: list[str] = []
        while True:
            try:
                received.append(q.get_nowait())
            except queue.Empty:
                break
        assert received == [], (
            f"AC7a: every API-route file mutation must produce zero SSE events on "
            f"the bus (self-write suppression covers target + parent dir); got {received}"
        )
    finally:
        bus.unsubscribe(q)
print(
    "PASS  AC7a: every API-route file-CRUD mutation produces zero SSE 'change' "
    "events on the bus (storage _mark_write + watcher was_recently_written)"
)


# --- AC7b: external file mutation -> exactly one event per tab after DEBOUNCE ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    bus = app.extensions["bus"]

    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

    q1 = bus.subscribe()
    q2 = bus.subscribe()
    try:
        for q in (q1, q2):
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

        # External file-mutation burst that BYPASSES Storage (no _mark_write
        # involvement). The watcher should detect it, debounce the burst,
        # and publish exactly one "change" per open tab.
        target_dir = root / "Alpha" / "Mod"
        for i in range(3):
            (target_dir / f"ext_{i}.feature").write_text(
                "Feature: ext\n  desc\n\n  Scenario: s\n    Given step\n",
                encoding="utf-8",
            )
        t_last_write = time.monotonic()

        msg1 = q1.get(timeout=3.0)
        t_msg = time.monotonic()
        msg2 = q2.get(timeout=3.0)
        assert msg1 == "change", f"AC7b: q1 message must be 'change', got {msg1!r}"
        assert msg2 == "change", f"AC7b: q2 message must be 'change', got {msg2!r}"

        # Burst collapsed to ONE event per tab.
        time.sleep(DEBOUNCE_SECONDS * 3)
        extra1: list[str] = []
        extra2: list[str] = []
        while True:
            try:
                extra1.append(q1.get_nowait())
            except queue.Empty:
                break
        while True:
            try:
                extra2.append(q2.get_nowait())
            except queue.Empty:
                break
        assert extra1 == [] and extra2 == [], (
            f"AC7b: external file-mutation burst must collapse to exactly ONE "
            f"event per open tab; got extras q1={extra1}, q2={extra2}"
        )

        delta = t_msg - t_last_write
        assert delta >= DEBOUNCE_SECONDS * 0.9, (
            f"AC7b: 'change' arrived too early; delta={delta:.4f}s, "
            f"expected >= DEBOUNCE_SECONDS * 0.9 = {DEBOUNCE_SECONDS * 0.9:.4f}s"
        )
    finally:
        bus.unsubscribe(q1)
        bus.unsubscribe(q2)
print(
    "PASS  AC7b: external file mutation -> exactly one 'change' event per open tab, "
    "no sooner than DEBOUNCE_SECONDS after the last write"
)
