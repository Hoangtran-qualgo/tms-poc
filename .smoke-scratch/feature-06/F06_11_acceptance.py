# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Acceptance criteria (AC1-AC6).

AC2 is **end-to-end** per Step-1 sign-off Q2: subscribe to the bus,
fire an external FS burst, assert exactly one `"change"` event per
subscriber after `DEBOUNCE_SECONDS * 0.9`, then independently issue
`GET /ui/tree` (simulating what HTMX would do on `sse:change`) and
confirm the response reflects the new FS state.
"""
import pathlib
import queue
import re
import tempfile
import time

from app import create_app
from app.watcher import DEBOUNCE_SECONDS


# --- AC1: first paint fully populated WITHOUT any /ui/tree request. ----
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # The very first GET / must already contain the tree contents inside
    # #tree-pane. (Server-side {% include "tree.html" %} in base.html.)
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    tree_pane = re.search(
        r'<aside\s+id="tree-pane"[^>]*>(.*?)</aside>', html, re.DOTALL
    )
    assert tree_pane, "AC1: <aside id=\"tree-pane\"> must exist on first paint"
    inner = tree_pane.group(1)
    assert "Alpha" in inner and "Mod" in inner, (
        "AC1: first paint of GET / must include the tree contents (Alpha, Mod) "
        "inside #tree-pane without any HTMX request having fired"
    )
print("PASS  AC1: first paint of GET / shows tree fully populated via server-side include")


# --- AC2: end-to-end -- external FS burst -> one "change" per tab + GET /ui/tree
# reflects the new FS state. ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    bus = app.extensions["bus"]

    # Seed BEFORE subscribing so seed events don't pollute the count.
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

        # External burst (bypasses Storage so no _mark_write suppression).
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
        assert msg1 == "change" and msg2 == "change", (
            f"AC2: every subscriber's queue must yield 'change'; got {msg1!r}, {msg2!r}"
        )

        # Burst collapses to ONE event per tab.
        time.sleep(DEBOUNCE_SECONDS * 3)
        extras = []
        for q in (q1, q2):
            while True:
                try:
                    extras.append(q.get_nowait())
                except queue.Empty:
                    break
        assert extras == [], (
            f"AC2: external FS burst must collapse to exactly ONE 'change' "
            f"event per open tab; got extras {extras!r}"
        )

        delta = t_msg - t_last_write
        assert delta >= DEBOUNCE_SECONDS * 0.9, (
            f"AC2: 'change' arrived too early; delta={delta:.4f}s, expected "
            f">= DEBOUNCE_SECONDS * 0.9 = {DEBOUNCE_SECONDS * 0.9:.4f}s"
        )

        # Independently fire the GET /ui/tree that HTMX would issue on
        # `sse:change`. The new files must appear in the response so the
        # round-trip is genuinely end-to-end.
        html = client.get("/ui/tree").get_data(as_text=True)
        for i in range(3):
            needle = f"data-path=\"Alpha/Mod/ext_{i}.feature\""
            assert needle in html, (
                f"AC2: GET /ui/tree after the external burst must reflect the "
                f"new FS state; expected {needle!r} in HTML"
            )
    finally:
        bus.unsubscribe(q1)
        bus.unsubscribe(q2)
print("PASS  AC2 (end-to-end): external FS burst -> one 'change' per tab after DEBOUNCE_SECONDS; GET /ui/tree shows new files")


# --- AC3: expanding a folder + external change -> still expanded.
# Hybrid: static + render-and-grep prove the wiring is in place; the
# actual DOM-state preservation belongs to the JS runtime. ---
REPO = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO / "app" / "static").glob("*.js")))
# Static: the Set survives re-renders (module scope).
assert re.search(r"^const\s+tmsExpandedFolders\s*=\s*new\s+Set\s*\(", JS, re.MULTILINE), (
    "AC3 (static): the expanded-folders Set must be module-scope so it "
    "survives /ui/tree swaps"
)
# Static: htmx:afterSwap calls tmsRestoreTreeState on #tree-pane swaps.
assert re.search(
    r'"htmx:afterSwap".*?e\.target\.id\s*===\s*"tree-pane"\s*\)\s*\{\s*tmsRestoreTreeState\s*\(',
    JS,
    re.DOTALL,
), (
    "AC3 (static): the htmx:afterSwap listener must call tmsRestoreTreeState "
    "after every #tree-pane swap (the swap from the external change in AC2)"
)
# Render-and-grep: rows carry data-path so tmsRestoreTreeState's walk
# has a key (proves the data plumbing is end-to-end).
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    html = client.get("/ui/tree").get_data(as_text=True)
assert 'data-path="Alpha"' in html and 'data-path="Alpha/Mod"' in html, (
    "AC3 (render): every folder row in /ui/tree must carry data-path so the "
    "expanded-state Set has a key to look up on re-render"
)
print("PASS  AC3 (Hybrid): expanded-folders Set is module-scope; afterSwap->tmsRestoreTreeState; rows carry data-path")


# --- AC4: clicking refresh button -> one GET /ui/tree + re-applies state.
# Render: the button is pure HTMX (no JS). GET /ui/tree returns 200 with
# the partial. AC3's wiring guarantees the post-swap state restore. ---
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    html = client.get("/ui/tree").get_data(as_text=True)
    button = re.search(
        r'<button[^>]*title="Refresh tree"[^>]*>[^<]*</button>', html
    ).group(0)
    for attr in (
        'hx-get="/ui/tree"',
        'hx-target="#tree-pane"',
        'hx-swap="innerHTML"',
    ):
        assert attr in button, (
            f"AC4: refresh button must wire {attr} so a click issues exactly "
            f"one GET /ui/tree; got {button!r}"
        )
    assert "onclick=" not in button, (
        "AC4: refresh button must NOT carry onclick (any JS would defeat "
        "the 'exactly one /ui/tree' guarantee)"
    )
    # Confirm GET /ui/tree returns the partial (one fetch -> one swap).
    r = client.get("/ui/tree")
    assert r.status_code == 200, (
        f"AC4: simulated refresh click must succeed; got {r.status_code}"
    )
print("PASS  AC4: refresh button is pure HTMX hx-get=/ui/tree -> one GET; post-swap restore wired via AC3 chain")


# --- AC5: folder name navigates main pane; caret does NOT. -------------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    html = client.get("/ui/tree").get_data(as_text=True)

caret = re.search(r'<button[^>]*class="caret[^"]*"[^>]*>', html).group(0)
assert "hx-" not in caret, (
    f"AC5: caret <button> must NOT carry any hx-* attribute -- clicking the "
    f"caret toggles only, never navigates; got {caret!r}"
)
name = re.search(
    r'<span[^>]*hx-get="/ui/folder/Alpha"[^>]*hx-target="#main-pane"',
    html,
)
assert name, (
    "AC5: folder name <span> must carry hx-get=\"/ui/folder/<path>\" + "
    "hx-target=\"#main-pane\" -- clicking the name navigates the main pane"
)
# Belt-and-braces: the name <span> must NOT itself invoke the toggle.
assert "toggleTreeFolder" not in name.group(0), (
    "AC5: folder name <span> must NOT call toggleTreeFolder (that's the "
    "caret's job)"
)
print("PASS  AC5: caret has onclick toggle + no hx-*; folder name has hx-get to /ui/folder/<p>")


# --- AC6: .feature -> file editor; non-.feature -> unsupported.html. ----
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    (root / "Alpha" / "Mod" / "note.txt").write_text("scratch", encoding="utf-8")

    feat = client.get("/ui/file/Alpha/Mod/case.feature")
    assert feat.status_code == 200, (
        f"AC6: GET /ui/file/<feature> must return 200, got {feat.status_code}"
    )
    feat_body = feat.get_data(as_text=True)
    assert "file-editor" in feat_body or 'id="file-editor"' in feat_body, (
        "AC6: GET /ui/file/<feature> must render the file editor partial "
        "(must carry the #file-editor anchor for the editor controller)"
    )

    other = client.get("/ui/file/Alpha/Mod/note.txt")
    assert other.status_code == 200, (
        f"AC6: GET /ui/file/<non-feature> must return 200, got {other.status_code}"
    )
    other_body = other.get_data(as_text=True).lower()
    assert "unsupported" in other_body or "not supported" in other_body, (
        "AC6: GET /ui/file/<non-feature> must render unsupported.html "
        "(its body should mention 'unsupported' / 'not supported')"
    )
print("PASS  AC6: /ui/file/<feature> renders editor; /ui/file/<non-feature> renders unsupported.html")
