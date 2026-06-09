"""2.e — External FS change under <project>/test-run/ publishes a "change"
event on the EventBus, AND a fresh GET /ui/test-run-tree reflects the new
group. Together with 2.h (which asserts the panel attaches hx-get +
hx-trigger="sse:change" on first mount), this proves the client will
re-render the panel on the next event."""
import os
import queue
import tempfile
import pathlib
import time
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    bus = app.extensions["bus"]

    # Seed a project with one group via the API (self-write, watcher
    # suppresses these). Use the API path so the EventBus is silent up
    # to here.
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")

    client = app.test_client()
    html_before = client.get("/ui/test-run-tree").get_data(as_text=True)
    assert "release-1" in html_before
    assert "release-2" not in html_before

    # Subscribe AFTER the seeding so we only catch the external change.
    q = bus.subscribe()
    try:
        # Drain any in-flight messages before the test action.
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                break

        # *** External *** mkdir — bypass Storage so was_recently_written
        # does NOT fire, and the watcher publishes a real "change".
        os.makedirs(root / "Alpha" / "test-run" / "release-2", exist_ok=False)

        # Watcher debounces 100 ms, plus FS event delivery slack.
        msg = q.get(timeout=2.0)
        assert msg == "change", msg
    finally:
        bus.unsubscribe(q)

    # The next /ui/test-run-tree fetch (what the client will do on the
    # sse:change event) reflects the new group.
    html_after = client.get("/ui/test-run-tree").get_data(as_text=True)
    assert "release-1" in html_after
    assert "release-2" in html_after
    print("PASS 2.e external change fires SSE + /ui/test-run-tree reflects it")
