# 03 · Watcher & SSE

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/watcher.py`, `app/sse.py`._

## Summary

Detects filesystem changes inside the data root, filters out the
app's own writes and atomic-write temp files, debounces bursts into
a single coalesced notification, and pushes that notification to
every connected browser tab over Server-Sent Events. The UI
responds to every notification by re-fetching the tree — the watcher
itself never describes *what* changed.

## Scope

In scope:

- Recursive `watchdog.Observer` over the data root.
- Event filtering: drop temp-file paths and self-writes.
- Single global `_DebouncedEmitter` that coalesces a burst into one
  publish.
- In-process `EventBus` (subscribe / publish / unsubscribe) with
  per-subscriber `queue.Queue`.
- SSE response generator with heartbeats and clean teardown on
  client disconnect.

Out of scope:

- Describing the change (no `{kind, path}` payload — the SSE event
  is the literal string `"change"`).
- Cross-process pub/sub (single-process, single-user product).
- Authentication of SSE clients (localhost-only deployment).

## Public surface

`app.watcher`:

- Class `EventBus()` with `subscribe() -> Queue[str]`,
  `unsubscribe(q)`, `publish(message: str) -> None`.
- Class `Watcher(storage, bus)` with `start()` and `stop()` —
  both idempotent.
- Constant `DEBOUNCE_SECONDS = 0.1`.

`app.sse`:

- Function `sse_response(bus: EventBus) -> Response` — Flask
  streaming response with `Content-Type: text/event-stream`.
- Constant `HEARTBEAT_INTERVAL_SECONDS = 15.0`.

Wired in `app/__init__.py`:

- `Watcher` constructed and started in `create_app`.
- `/api/events` route returns `sse_response(bus)`.

## Invariants & rules

**Event filtering (`_Handler._should_emit`)**

Drop any event whose paths are *all* outside the data root or
exactly equal the data root itself (macOS FSEvents bubbles
uninformative root-level `DirModifiedEvent`s).

Drop any event where any path matches `TEMP_FILE_RE`
(`.+\.tmp\.\d+\.[0-9a-f]+$`) — covers both sides of a rename.

Drop any event where any path passes `storage.was_recently_written`
(self-write suppression).

**Debouncing**

Single global `_DebouncedEmitter`. Every surviving event calls
`trigger()`, which cancels the pending timer and starts a fresh
`threading.Timer(DEBOUNCE_SECONDS, _fire)`. Only the last deadline
actually fires, then publishes the event name `"change"` on the
bus.

**EventBus**

Each subscriber gets its own unbounded `queue.Queue()`. `publish`
takes a snapshot of subscribers under the lock, then `put_nowait`s
to each — the `queue.Full` branch is unreachable today but kept for
defensive consistency.

**SSE response**

- Yields `: connected\n\n` on first iteration.
- Blocks on the subscriber queue with `timeout =
  HEARTBEAT_INTERVAL_SECONDS`; on timeout, yields a comment
  `: heartbeat\n\n` and loops.
- On message, yields `event: {message}\ndata: \n\n` (HTMX SSE
  extension matches `sse-swap="change"` against the event name).
- `finally: bus.unsubscribe(q)` runs on client disconnect or app
  teardown.

**Observer lifecycle**

- `Watcher.start()` constructs and starts a single `Observer`,
  scheduled recursively on the data root. The observer thread is a
  daemon so CTRL-C tears down cleanly even if `stop()` was never
  called.
- `Watcher.stop()` cancels the debounced emitter and joins the
  observer with a 2 s timeout.

## Affects

- `02-storage-core`: reads `Storage.was_recently_written` and
  `TEMP_FILE_RE`; the contract between the two modules is
  documented in storage's "self-write bookkeeping" rule.
- `06-tree-pane`: the *only* feature whose UI is wired to
  `sse-swap="change"` today. Every "change" event causes a tree
  re-fetch.
- All other UI features (folder views, file editor, search) are
  *indirectly* affected because a watcher notification triggers a
  tree refresh — but they do not subscribe to SSE themselves.

## Depends on

- `02-storage-core` for `was_recently_written` and `TEMP_FILE_RE`.
- `watchdog >=4,<7` for the cross-platform observer.
- Python stdlib `queue`, `threading`, `time`.
- The single-process, threaded Flask runtime. The current `EventBus`
  is in-memory; horizontal scaling would require replacing it.

## Surface for follow-up

- Per-event payloads (`{kind, path, is_dir}`) are not emitted
  today. The current consumers (tree pane, test-run sidebar, file
  editor, run editor) all refetch their full state on any
  `"change"` message; this is fine while the page count is small
  but becomes wasteful at scale. A future feature that needs to
  react to a *specific* file change (e.g. "this test case was
  just modified, highlight only that row") would need to extend
  the bus protocol from `str` to a richer message, then teach the
  SSE generator and the HTMX / JS wiring about the new event
  name(s).
- Multi-tab support is already free (each tab calls `subscribe()`
  and gets its own queue). Multi-process is not — a future
  deployment behind multiple workers would need to swap the bus
  for a Redis pub/sub (or similar).
- Bounded queues with overflow policies are wired in shape but not
  in value (`queue.Full` branch exists). A future stress profile
  may want to cap subscriber queue length and drop oldest.

## Acceptance criteria

- A user-initiated save via the editor produces zero SSE events on
  any open tab (covered by `_mark_write` + `TEMP_FILE_RE`).
- An out-of-band edit (e.g. `echo … > project/p/m/x.feature` in the
  terminal) produces exactly one `"change"` event on every open
  tab, no sooner than `DEBOUNCE_SECONDS` after the last write in
  the burst.
- Closing a browser tab unsubscribes its queue (verified by
  inspecting `EventBus._subscribers` length).
- An idle connection receives a `: heartbeat\n\n` comment every
  `HEARTBEAT_INTERVAL_SECONDS`.
- `Watcher.start()` and `Watcher.stop()` are idempotent — calling
  either twice is a no-op.
