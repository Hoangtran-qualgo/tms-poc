# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / SSE response (SS1-SS4)."""
import time

from app import sse as sse_mod
from app.sse import sse_response
from app.watcher import EventBus


# --- SS1: first iteration yields b': connected\n\n' ---
bus = EventBus()
response = sse_response(bus)
gen = response.response  # the underlying generator wrapped by flask.Response
first = next(gen)
assert first == b": connected\n\n", (
    f"SS1: first chunk must be b': connected\\n\\n', got {first!r}"
)
gen.close()
print("PASS  SS1: first iteration yields b': connected\\n\\n'")


# --- SS2: idle iteration yields b': heartbeat\n\n' after HEARTBEAT_INTERVAL_SECONDS ---
original = sse_mod.HEARTBEAT_INTERVAL_SECONDS
try:
    sse_mod.HEARTBEAT_INTERVAL_SECONDS = 0.1  # tighten so the test doesn't wait 15 s

    bus = EventBus()
    response = sse_response(bus)
    gen = response.response

    assert next(gen) == b": connected\n\n"

    # No publishes -> q.get(timeout=0.1) raises queue.Empty -> heartbeat is yielded.
    t0 = time.monotonic()
    second = next(gen)
    dt = time.monotonic() - t0
    assert second == b": heartbeat\n\n", (
        f"SS2: idle chunk must be b': heartbeat\\n\\n', got {second!r}"
    )
    assert dt >= 0.1 * 0.9, (
        f"SS2: heartbeat should arrive after ~HEARTBEAT_INTERVAL_SECONDS (0.1 s), got {dt:.3f} s"
    )
    gen.close()
finally:
    sse_mod.HEARTBEAT_INTERVAL_SECONDS = original
print("PASS  SS2: idle iteration yields b': heartbeat\\n\\n' after HEARTBEAT_INTERVAL_SECONDS")


# --- SS3: on a published message, yields b'event: {message}\ndata: \n\n' ---
bus = EventBus()
response = sse_response(bus)
gen = response.response
assert next(gen) == b": connected\n\n"

bus.publish("change")
chunk = next(gen)
assert chunk == b"event: change\ndata: \n\n", (
    f"SS3: message chunk must be b'event: change\\ndata: \\n\\n', got {chunk!r}"
)

# Arbitrary message string flows through unchanged (HTMX picks the event name).
bus.publish("custom_event")
chunk2 = next(gen)
assert chunk2 == b"event: custom_event\ndata: \n\n", (
    f"SS3: arbitrary message must be echoed, got {chunk2!r}"
)
gen.close()
print("PASS  SS3: on message, yields b'event: {message}\\ndata: \\n\\n'")


# --- SS4: finally bus.unsubscribe(q) runs on client disconnect / teardown ---
bus = EventBus()
assert bus._subscribers == [], "SS4 setup: bus must start empty"

response = sse_response(bus)
# `sse_response` subscribes synchronously, before the generator is iterated.
assert len(bus._subscribers) == 1, (
    f"SS4: sse_response must subscribe immediately, got {len(bus._subscribers)} subscribers"
)

gen = response.response
next(gen)  # enter the try: block by yielding ": connected"

# Closing the generator runs the finally clause.
gen.close()
assert len(bus._subscribers) == 0, (
    f"SS4: closing the generator must unsubscribe; subscribers={len(bus._subscribers)}"
)
print("PASS  SS4: finally bus.unsubscribe(q) runs on generator close")
