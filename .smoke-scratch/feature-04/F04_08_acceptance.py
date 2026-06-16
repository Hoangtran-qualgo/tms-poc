# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / Acceptance criteria (AC1-AC6).

AC6 is split per Step-1 sign-off into:
- AC6a: API-route mutation -> zero SSE events on the bus (suppression).
- AC6b: external mutation -> exactly one SSE event per open tab after
        DEBOUNCE_SECONDS (detection).
"""
import os
import pathlib
import queue
import tempfile
import time

from app import create_app
from app.watcher import DEBOUNCE_SECONDS


# --- AC1: forbidden char -> 400 bad_request ---------------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    r = client.post("/api/folders", json={"name": "bad:name"})
    assert r.status_code == 400, (
        f"AC1: forbidden-char POST must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request", (
        f"AC1: forbidden-char POST must carry error.code='bad_request', got {r.get_json()!r}"
    )
print("PASS  AC1: creating a folder with a forbidden character returns 400 with code='bad_request'")


# --- AC2: depth 11 -> 400 bad_request --------------------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    segments: list[str] = []
    for i in range(1, 11):
        client.post("/api/folders", json={"parent": "/".join(segments), "name": f"d{i}"})
        segments.append(f"d{i}")
    # Now at depth 10. Push depth 11.
    r = client.post(
        "/api/folders",
        json={"parent": "/".join(segments), "name": "d11"},
    )
    assert r.status_code == 400, (
        f"AC2: depth-11 POST must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request", (
        "AC2: depth-11 POST must carry error.code='bad_request'"
    )
print("PASS  AC2: creating a folder at depth 11 returns 400 with code='bad_request'")


# --- AC3: duplicate -> 409 name_conflict -----------------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    r = client.post("/api/folders", json={"name": "Alpha"})
    assert r.status_code == 409, (
        f"AC3: duplicate POST must return 409, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "name_conflict", (
        "AC3: duplicate POST must carry error.code='name_conflict'"
    )
print("PASS  AC3: creating a duplicate folder in same parent returns 409 with code='name_conflict'")


# --- AC4: DELETE removes every descendant file and folder ------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # Build Alpha/Mod/Sub with a .feature file and another nested folder.
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case",
              "scenario_name": "seed", "description": "seed"},
    )
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod/Sub", "file_name": "deep_case",
              "scenario_name": "seed", "description": "seed"},
    )

    descendants = [
        root / "Alpha" / "Mod",
        root / "Alpha" / "Mod" / "Sub",
        root / "Alpha" / "Mod" / "case.feature",
        root / "Alpha" / "Mod" / "Sub" / "deep_case.feature",
    ]
    for p in descendants:
        assert p.exists(), f"AC4 setup: descendant {p} must exist before delete"

    r = client.delete("/api/folders/Alpha")
    assert r.status_code == 204, f"AC4: DELETE must return 204, got {r.status_code}"
    for p in descendants + [root / "Alpha"]:
        assert not p.exists(), (
            f"AC4: descendant {p.relative_to(root)} must be gone after recursive delete"
        )
print("PASS  AC4: deleting a folder removes every descendant file and folder")


# --- AC5: DELETE non-existent -> 204 (idempotent) --------------------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    r = client.delete("/api/folders/never_existed")
    assert r.status_code == 204, (
        f"AC5: DELETE missing folder must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "AC5: idempotent DELETE body must be empty"
print("PASS  AC5: deleting a non-existent folder returns 204 (idempotent)")


# --- AC6a: API mutation -> zero SSE events on the bus ----------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    bus = app.extensions["bus"]

    # Seed before subscribing so seeding's FS events aren't measured.
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

    q = bus.subscribe()
    try:
        # Drain any in-flight events from the seeding burst.
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                break

        # Each API mutation: must produce ZERO events because storage's
        # _mark_write + the watcher's was_recently_written suppresses
        # the resulting FS events.
        r = client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
        assert r.status_code == 201
        r = client.patch("/api/folders/Alpha/Mod/Sub", json={"name": "Renamed"})
        assert r.status_code == 200
        r = client.delete("/api/folders/Alpha/Mod/Renamed")
        assert r.status_code == 204

        # Wait well past DEBOUNCE_SECONDS plus FS-event slack.
        time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

        received: list[str] = []
        while True:
            try:
                received.append(q.get_nowait())
            except queue.Empty:
                break
        assert received == [], (
            f"AC6a: API-route folder mutations (POST/PATCH/DELETE) must produce "
            f"zero SSE events on the bus (self-write suppression); got {received}"
        )
    finally:
        bus.unsubscribe(q)
print(
    "PASS  AC6a: API-route folder mutations (POST/PATCH/DELETE /api/folders) "
    "produce zero SSE 'change' events on the bus"
)


# --- AC6b: external mutation -> exactly one SSE event per tab after DEBOUNCE ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    bus = app.extensions["bus"]

    # Seed a depth-2 module so we have somewhere "external" to write under.
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

    # Two open tabs -> two subscribers; both must receive the event.
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    try:
        for q in (q1, q2):
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

        # External burst: create three folders directly via os.makedirs
        # so the watcher (NOT storage) is the one to detect them. Storage's
        # _mark_write is not called, so was_recently_written returns False
        # and the events propagate through the debouncer.
        target_parent = root / "Alpha" / "Mod"
        for i in range(3):
            os.makedirs(target_parent / f"ext_{i}")
        t_last_write = time.monotonic()

        msg1 = q1.get(timeout=3.0)
        t_msg = time.monotonic()
        msg2 = q2.get(timeout=3.0)
        assert msg1 == "change", f"AC6b: q1 message must be 'change', got {msg1!r}"
        assert msg2 == "change", f"AC6b: q2 message must be 'change', got {msg2!r}"

        # No further events in the next debounce window (burst collapsed to ONE).
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
            f"AC6b: external folder-mutation burst must collapse to exactly ONE "
            f"event per open tab; got extras q1={extra1}, q2={extra2}"
        )

        # Timing lower bound: publish no sooner than DEBOUNCE_SECONDS after
        # the last write (10% slack approved in Step-1 sign-off for f3).
        delta = t_msg - t_last_write
        assert delta >= DEBOUNCE_SECONDS * 0.9, (
            f"AC6b: 'change' arrived too early; delta={delta:.4f}s, "
            f"expected >= DEBOUNCE_SECONDS * 0.9 = {DEBOUNCE_SECONDS * 0.9:.4f}s"
        )
    finally:
        bus.unsubscribe(q1)
        bus.unsubscribe(q2)
print(
    "PASS  AC6b: an external folder mutation produces exactly one 'change' event "
    "per open tab, no sooner than DEBOUNCE_SECONDS after the last write"
)
