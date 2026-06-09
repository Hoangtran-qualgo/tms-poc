# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / EventBus (EB1-EB2)."""
import queue

from app.watcher import EventBus


# --- EB1: each subscriber gets its own unbounded queue.Queue ---
bus = EventBus()
q1 = bus.subscribe()
q2 = bus.subscribe()

assert isinstance(q1, queue.Queue), f"EB1: subscribe() must return a queue.Queue, got {type(q1).__name__}"
assert isinstance(q2, queue.Queue), f"EB1: subscribe() must return a queue.Queue, got {type(q2).__name__}"
assert q1 is not q2, "EB1: each subscriber must receive a distinct queue instance"
# Unbounded: queue.Queue() with no maxsize has maxsize == 0 (the sentinel for unlimited).
assert q1.maxsize == 0, f"EB1: queue must be unbounded (maxsize == 0), got {q1.maxsize}"
assert q2.maxsize == 0, f"EB1: queue must be unbounded (maxsize == 0), got {q2.maxsize}"

# Both queues are tracked in _subscribers.
assert len(bus._subscribers) == 2, f"EB1: expected 2 subscribers, got {len(bus._subscribers)}"
assert q1 in bus._subscribers and q2 in bus._subscribers, "EB1: both queues must be in _subscribers"
print("PASS  EB1: each subscriber receives its own unbounded queue.Queue")


# --- EB2: publish snapshots subscribers and put_nowaits to each ---
bus.publish("hello")
m1 = q1.get_nowait()
m2 = q2.get_nowait()
assert m1 == "hello" and m2 == "hello", (
    f"EB2: every live subscriber must receive the published message, got {m1!r} / {m2!r}"
)

# A third subscriber added AFTER the publish does NOT receive the prior message.
q3 = bus.subscribe()
assert q3.empty(), "EB2: a subscriber added after publish must not receive the prior message"

# Fan-out to all THREE on the next publish.
bus.publish("again")
assert q1.get_nowait() == "again", "EB2: q1 missed second publish"
assert q2.get_nowait() == "again", "EB2: q2 missed second publish"
assert q3.get_nowait() == "again", "EB2: q3 missed second publish"

# unsubscribe removes the queue from _subscribers.
bus.unsubscribe(q2)
assert q2 not in bus._subscribers, "EB2: unsubscribe must remove the queue from _subscribers"
assert len(bus._subscribers) == 2, (
    f"EB2: _subscribers length should decrement on unsubscribe, got {len(bus._subscribers)}"
)

# A publish AFTER unsubscribe does not reach the unsubscribed queue.
bus.publish("post-unsub")
assert q1.get_nowait() == "post-unsub", "EB2: still-subscribed q1 must receive"
assert q3.get_nowait() == "post-unsub", "EB2: still-subscribed q3 must receive"
assert q2.empty(), "EB2: unsubscribed q2 must NOT receive subsequent publishes"

# Double-unsubscribe is a no-op (spec-gap behaviour observed in code; defensive).
bus.unsubscribe(q2)  # should not raise

# Clean up.
bus.unsubscribe(q1)
bus.unsubscribe(q3)
assert bus._subscribers == [], f"EB2 cleanup: expected empty subscriber list, got {bus._subscribers}"
print("PASS  EB2: publish fan-outs to all subscribers under a snapshot; unsubscribe removes cleanly")
