"""SSE response helper for the ``/api/events`` endpoint.

The route handler in ``server.py`` subscribes to the shared
:class:`~app.watcher.EventBus` and streams ``change`` events to the HTMX
``sse-swap="change"`` consumer in ``base.html``.
"""

from __future__ import annotations

import queue
from typing import Iterator

from flask import Response

from .watcher import EventBus

#: How long a subscriber blocks on its queue before emitting an SSE
#: comment ("heartbeat"). The heartbeat keeps intermediate proxies
#: from closing idle connections and gives the server a chance to
#: notice a disconnected client at this cadence.
HEARTBEAT_INTERVAL_SECONDS: float = 15.0


def sse_response(bus: EventBus) -> Response:
    """Build a streaming SSE :class:`Response` backed by ``bus``.

    Emits one SSE event per ``bus.publish('change')`` call (with ``event``
    field set to the published string and an empty ``data`` line, which is
    what the HTMX SSE extension consumes). When the bus is idle for
    :data:`HEARTBEAT_INTERVAL_SECONDS`, a comment line is emitted instead.

    The subscriber's queue is unsubscribed in the generator's ``finally`` so
    the bookkeeping is cleaned up on client disconnect or app teardown.
    """

    q = bus.subscribe()

    def stream() -> Iterator[bytes]:
        try:
            # An initial comment line proves the stream is open to the client
            # without waiting for the first real event.
            yield b": connected\n\n"
            while True:
                try:
                    message = q.get(timeout=HEARTBEAT_INTERVAL_SECONDS)
                except queue.Empty:
                    yield b": heartbeat\n\n"
                    continue
                # HTMX SSE matches `sse-swap="change"` against the event name.
                payload = f"event: {message}\ndata: \n\n".encode("utf-8")
                yield payload
        finally:
            bus.unsubscribe(q)

    response = Response(stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    # Disable proxy buffering (nginx-style) so SSE messages flush immediately.
    response.headers["X-Accel-Buffering"] = "no"
    return response
