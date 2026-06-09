# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / Observer lifecycle (OL1, OL2)."""
import os
import pathlib
import tempfile

from watchdog.observers.api import BaseObserver

from app.storage import Storage
from app.watcher import EventBus, Watcher


# --- OL1: start() constructs a single Observer, scheduled recursively, daemon ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)

    # Before start(): no observer.
    assert w._observer is None, "OL1: _observer must be None before start()"

    w.start()
    try:
        obs = w._observer
        assert obs is not None, "OL1: start() must construct an Observer"
        assert isinstance(obs, BaseObserver), (
            f"OL1: _observer must be a watchdog BaseObserver, got {type(obs).__name__}"
        )
        assert obs.is_alive(), "OL1: observer thread must be alive after start()"
        assert obs.daemon, "OL1: observer thread must be a daemon thread"

        # Behavioural proof that the observer is scheduled RECURSIVELY on the
        # data root: an out-of-band create in a NESTED subdirectory reaches
        # the handler and produces a 'change' event on the bus. If recursive
        # were False (or the path were wrong) this would time out.
        q = bus.subscribe()
        try:
            os.makedirs(root / "external_proj" / "deep" / "nested", exist_ok=False)
            msg = q.get(timeout=3.0)
            assert msg == "change", f"OL1: nested external event should publish 'change', got {msg!r}"
        finally:
            bus.unsubscribe(q)
    finally:
        # Always clean up the observer before leaving the tempdir.
        w.stop()
print("PASS  OL1: start() constructs a daemon Observer scheduled recursively on the data root")


# --- OL2: stop() cancels the debounced emitter and tears the observer down ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)

    w.start()
    obs_before = w._observer
    assert obs_before is not None and obs_before.is_alive(), "OL2 setup: observer must be running"

    # Plant a pending debounce timer so OL2 can verify the cancel() path.
    w._emitter.trigger()
    assert w._emitter._timer is not None, "OL2 setup: a pending timer must exist before stop()"

    w.stop()

    assert w._observer is None, "OL2: _observer must be reset to None after stop()"
    # The Observer thread should have terminated within stop()'s 2 s join window.
    assert not obs_before.is_alive(), (
        "OL2: previously-running observer thread must be dead after stop() (join timeout = 2 s)"
    )
    assert w._emitter._timer is None, (
        "OL2: stop() must cancel the debounced emitter (timer set to None)"
    )
print("PASS  OL2: stop() cancels the debounced emitter and joins the observer")
