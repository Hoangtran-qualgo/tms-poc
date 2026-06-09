# feature-03 · Watcher & SSE — coverage matrix

Step 1 audit of the smoke tests against
`specs/features/03-feature-watcher-and-sse-NEW.md`.

## Method

- Spec source: `specs/features/03-feature-watcher-and-sse-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Bundled bullets split when sub-clauses are independently
  testable.
- `Status` values: `covered`, `partial` (incidental coverage
  inside a primary-other-feature smoke), `missing`, `n/a`
  (rule is documentation-only / not testable).
- `Smoke file` column carries the target file for every row.
  Per Decision A, feature-03 uses **one smoke per spec
  section** — six files total (`F03_01_event_filtering.py`
  … `F03_06_acceptance.py`). All six exist as of Step 4
  (Jun 8, 2026).

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| EF1 | Drop any event whose paths are *all* outside the data root, or which equals the data root itself. (macOS FSEvents bubbles uninformative root-level `DirModifiedEvent`s.) | Event filtering | `F03_01_event_filtering.py` (+ incidental in `p2_2e_sse_picks_up_external_change.py`) | covered |
| EF2 | Drop any event where any path matches `TEMP_FILE_RE` (`.+\.tmp\.\d+\.[0-9a-f]+$`) — covers both sides of a rename. | Event filtering | `F03_01_event_filtering.py` | covered |
| EF3 | Drop any event where any path passes `storage.was_recently_written` (self-write suppression). | Event filtering | `F03_01_event_filtering.py` | covered |
| DB1 | Single global `_DebouncedEmitter` instance owned by the `Watcher`. | Debouncing | `F03_02_debouncing.py` | covered |
| DB2 | `trigger()` cancels the pending `threading.Timer` (if any) and starts a fresh `threading.Timer(DEBOUNCE_SECONDS, _fire)`. | Debouncing | `F03_02_debouncing.py` | covered |
| DB3 | Only the last deadline actually fires — bursts of N triggers within the window collapse to one `_fire`. | Debouncing | `F03_02_debouncing.py` | covered |
| DB4 | `_fire` publishes the literal string `"change"` on the bus. | Debouncing | `F03_02_debouncing.py` (+ incidental in `p2_2e_sse_picks_up_external_change.py`) | covered |
| EB1 | Each subscriber receives its own unbounded `queue.Queue()` instance from `subscribe()`. | EventBus | `F03_03_event_bus.py` (+ incidental in `p2_2e_sse_picks_up_external_change.py`) | covered |
| EB2 | `publish` snapshots subscribers under the lock then `put_nowait`s to each. (Multi-subscriber fan-out.) | EventBus | `F03_03_event_bus.py` (+ incidental in `p2_2e_sse_picks_up_external_change.py`) | covered |
| SS1 | `sse_response` yields `: connected\n\n` on the first iteration. | SSE response | `F03_04_sse_response.py` | covered |
| SS2 | Blocks on the subscriber queue with `timeout = HEARTBEAT_INTERVAL_SECONDS`; on timeout, yields `: heartbeat\n\n` and loops. | SSE response | `F03_04_sse_response.py` | covered |
| SS3 | On a queue message, yields `event: {message}\ndata: \n\n` (HTMX SSE extension format). | SSE response | `F03_04_sse_response.py` | covered |
| SS4 | `finally: bus.unsubscribe(q)` runs on client disconnect / app teardown — the subscriber queue is removed from `bus._subscribers`. | SSE response | `F03_04_sse_response.py` | covered |
| OL1 | `Watcher.start()` constructs and starts a single `Observer`, scheduled recursively on the data root; the observer thread is a daemon. | Observer lifecycle | `F03_05_observer_lifecycle.py` (+ incidental in `p2_2e_sse_picks_up_external_change.py`) | covered |
| OL2 | `Watcher.stop()` cancels the debounced emitter and joins the observer with a 2 s timeout. | Observer lifecycle | `F03_05_observer_lifecycle.py` | covered |
| AC1 | A user-initiated save via the editor produces zero SSE events on any open tab. (Combines EF2 + EF3 end-to-end.) | Acceptance criteria | `F03_06_acceptance.py` | covered |
| AC2 | An out-of-band edit produces exactly one `"change"` event per open tab, no sooner than `DEBOUNCE_SECONDS` after the last write in the burst. (Strengthens EF1 + DB1–4 + EB1–2.) | Acceptance criteria | `F03_06_acceptance.py` | covered |
| AC3 | Closing a browser tab unsubscribes its queue, verified by inspecting `EventBus._subscribers` length. (Strengthens SS4 with the bookkeeping invariant.) | Acceptance criteria | `F03_06_acceptance.py` | covered |
| AC4 | An idle connection receives `: heartbeat\n\n` every `HEARTBEAT_INTERVAL_SECONDS`. (Strengthens SS2 with the cadence claim.) | Acceptance criteria | `F03_06_acceptance.py` | covered |
| AC5 | `Watcher.start()` and `Watcher.stop()` are idempotent — calling either twice is a no-op. (Strengthens OL1 + OL2.) | Acceptance criteria | `F03_06_acceptance.py` | covered |

## Summary

- Total rules: **20** (3 event filtering, 4 debouncing, 2 EventBus, 4 SSE response, 2 observer lifecycle, 5 acceptance).
- `covered`: **20**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-03 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 03`
exits zero with all six smokes green). The five previously
`partial` rows (EF1, DB4, EB1, EB2, OL1) are now fully
covered by feature-03's own primary-frame smokes; the
`p2_2e_sse_picks_up_external_change.py` file stays in its
feature-10 primary frame and provides redundant incidental
coverage.

## Notes & flags

- **One existing partial-coverage smoke.** `p2_2e_sse_picks_up_external_change.py`
  is primary-feature-10 (`test-run`) but exercises the
  watcher / bus pipeline end-to-end. It asserts:
  - `bus.subscribe()` returns a usable queue (EB1).
  - An out-of-band `os.makedirs` inside the data root
    eventually publishes `msg == "change"` on the bus
    within 2.0 s (EF1 + DB4, with debounce + FS-event
    delivery slack).
  - It does **not** assert: multi-subscriber fan-out (EB2
    is only partially exercised — single subscriber),
    the suppression path (self-writes are bypassed by
    subscribing *after* seeding, not by relying on
    `was_recently_written`), nor any timing claim about
    the debounce window itself.
- **Step 2 will be a no-op `git mv`.** Feature-03 has zero
  smokes whose *primary frame* is feature-03; the partial
  coverage above stays in the feature-10 dir.
- **Pre-approval requested for monkey-patching SSE constants.**
  `HEARTBEAT_INTERVAL_SECONDS = 15.0` is too long for a
  smoke. SS2 / SS4 / AC4 will set
  `app.sse.HEARTBEAT_INTERVAL_SECONDS = 0.1` (or similar)
  for the duration of their tests and restore on teardown.
  The constant is read at call time via the module global,
  so the patch takes effect immediately.
- **FS-event flakiness budget.** Tests that rely on real
  `watchdog.Observer` events (EF1/EF2/EF3, DB3, AC1/AC2,
  OL1/OL2) need generous timeouts (1.0–3.0 s typical) to
  ride out FS-event delivery jitter on macOS APFS. The
  `p2_2e_*` smoke uses 2.0 s and is stable; we will reuse
  that budget.
- **AC2 "no sooner than DEBOUNCE_SECONDS" assertion.** This
  is the only timing-LOWER-bound rule in the entire spec.
  Cleanest approach: record `t_last_write`, then after
  the first message arrives, assert `t_msg - t_last_write
  >= DEBOUNCE_SECONDS * 0.9` (10 % slack — debounce is a
  software timer and may fire fractionally early under
  `threading.Timer`'s implementation). Will flag for
  sign-off before coding.
- **`_DebouncedEmitter` is private.** DB1 ("single global
  emitter owned by the `Watcher`") is testable by reading
  `watcher._emitter` (private attr, but observable). Will
  treat that access the same way feature-02 treats `_locks`
  / `_recent_writes` — read-only inspection is permitted.
- **`EventBus._subscribers` is private** but the spec calls
  it out by name in AC3 ("verified by inspecting
  `EventBus._subscribers` length"), so direct access is
  spec-blessed for that row.
- **SS3 message format is exact.** `event: {message}\ndata:
  \n\n` includes a *space* after `event:` and after `data:`
  per the HTML5 spec; one trailing `\n\n` ends the SSE
  record. Will assert the exact byte string.
- **Spec gaps discovered during Step-1 re-review.** Behaviours
  present in `app/watcher.py` / `app/sse.py` but **not** in
  the spec:
  - `Cache-Control: no-cache` and `X-Accel-Buffering: no`
    response headers on the SSE response (`app/sse.py:56-58`).
    The spec's Public surface section mentions only
    `Content-Type: text/event-stream`.
  - `EventBus.unsubscribe(q)` swallows `ValueError` on
    double-unsubscribe, making the operation idempotent;
    spec doesn't state this.
  - `_DebouncedEmitter._timer.daemon = True` — the debounce
    timer is a daemon thread. The spec calls out the
    *observer* daemon flag explicitly (OL1) but not the
    debounce-timer daemon flag.
  - `Content-Type: text/event-stream` is in the spec's
    Public surface section but not under Invariants & rules.
    De-facto covered by SS1/SS2/SS3 tests that inspect the
    response body, so no dedicated rule added.
  - The `pragma: no cover` branch on `queue.Full` in
    `EventBus.publish` — spec acknowledges this as
    "unreachable today" so nothing to test.
  **These are not added to the matrix** — audit tests the
  spec as written. Surfaced for a follow-up spec patch.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-03:

- Six smoke files written, one per spec section, ~50–190
  lines each:
  - `F03_01_event_filtering.py` covers EF1–EF3 (3 rules).
  - `F03_02_debouncing.py` covers DB1–DB4 (4 rules).
  - `F03_03_event_bus.py` covers EB1–EB2 (2 rules).
  - `F03_04_sse_response.py` covers SS1–SS4 (4 rules).
  - `F03_05_observer_lifecycle.py` covers OL1–OL2 (2 rules).
  - `F03_06_acceptance.py` covers AC1–AC5 (5 rules).
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 03 --verbose` reports `6/6 passed; 0 failed`
  and all 20 rule-level `PASS  <id>: …` lines fire.
- Full-suite re-run (`run.py` without filter) reports
  `19/19 passed; 0 failed`, confirming no regression in
  features 01 / 02.
- **Per-rule notes:**
  - **EF1/EF2/EF3** drive `_Handler._should_emit` directly
    with synthesised `watchdog.events.*` instances. Since
    the handler inspects path strings only (no `os.stat`),
    test files never need to actually exist on disk. This
    avoids EF3 self-write side-effects from leaking into
    EF1 / EF2 setup.
  - **DB1/DB2** poke `Watcher._emitter` / `_emitter._timer`
    (private attrs). Per Step 1 sign-off, this read-only
    inspection is permitted (same precedent as feature-02's
    `_locks` / `_recent_writes` checks).
  - **DB3** uses a tight burst of 10 `trigger()` calls
    inside a 50 ms debounce window, then waits `DELAY * 3`
    and asserts exactly one publish.
  - **SS2/SS4/AC4** monkey-patch `app.sse.HEARTBEAT_INTERVAL_SECONDS`
    to 0.08–0.1 s for the duration of the test (per Step 1
    sign-off item 2). The constant is read at call time
    via the module global so the patch takes effect on the
    next `q.get(timeout=...)` call.
  - **SS3** asserts the exact byte string
    `b"event: {message}\ndata: \n\n"` including the
    spaces after `event:` and `data:`. A second publish
    with an arbitrary string verifies the message flows
    through unchanged (HTMX picks the event name).
  - **OL1** proves `recursive=True` on the data root
    behaviourally: an out-of-band `os.makedirs` in a
    nested subdirectory (depth 3) produces a `"change"`
    event within 3 s. Avoids poking watchdog internals.
  - **OL2** confirms the observer thread is dead after
    `stop()` (holds a reference to the thread before
    stopping) and that `_emitter._timer` is `None`.
  - **AC1** drives every storage mutation method
    (`create_file`, `write_raw`, `delete_file`) while a
    subscriber is listening and asserts zero events
    arrive within `max(DEBOUNCE_SECONDS * 3, 0.5)` s.
  - **AC2** uses the approved
    `t_msg - t_last_write >= DEBOUNCE_SECONDS * 0.9`
    lower-bound check (10 % slack for `threading.Timer`
    jitter). Verifies fan-out by using two subscribers
    and asserting both receive exactly one `"change"`.
  - **AC3** uses two `sse_response` calls (simulating two
    open tabs), iterates one chunk on each generator,
    then closes each in turn and asserts the subscriber
    count decrements correctly.
  - **AC4** measures three consecutive heartbeat intervals
    after monkey-patching `HEARTBEAT_INTERVAL_SECONDS` to
    0.08 s, each with the 10 % slack lower bound.
  - **AC5** verifies `stop()` before `start()` is a no-op,
    a second `start()` reuses the existing observer
    (`watcher._observer is obs_first`), and a second
    `stop()` does not raise.

**Feature-03 cycle complete.** Per the locked plan,
**feature-04 is next** — audit
`specs/features/04-*-NEW.md` (will need to discover the
exact filename in Step 1).

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-03:

1. **Rule list re-reviewed against spec + code.** 20 rules
   confirmed (EF×3, DB×4, EB×2, SS×4, OL×2, AC×5). No
   additions, no removals.
   Re-review corrections applied:
   - DB2: dropped unspec'd "(daemon)" qualifier (the code
     sets `_timer.daemon = True` but the spec doesn't).
   - EF1: clarified the `p2_2e_*` partial-coverage note
     to read `"don't drop" branch only — in-root event
     publishes` (the drop path is untested).
   Spec gaps found in code but not in spec (SSE headers,
   `unsubscribe` idempotence, debounce-timer daemon flag)
   surfaced in Notes & flags; **not** added to the matrix.
2. **Monkey-patch pre-approved** for
   `app.sse.HEARTBEAT_INTERVAL_SECONDS`. The constant is
   accessed via the module global at call time so a
   simple `app.sse.HEARTBEAT_INTERVAL_SECONDS = 0.1` patch
   (with restore on teardown) takes effect immediately on
   the next `q.get(timeout=...)` call inside the generator.
3. **AC2 timing assertion pre-approved**:
   `t_msg - t_last_write >= DEBOUNCE_SECONDS * 0.9` (10 %
   slack for `threading.Timer` jitter).
4. **Real-FS-event flakiness budget pre-approved**:
   2.0–3.0 s per timeout (matches the `p2_2e_*` precedent).

Ready for **Step 2 (Restructure)** — no-op `git mv`
(zero feature-03 primary smokes; the `p2_2e_*` file
stays in feature-10's primary frame). Cycle proceeds
directly to Step 4 to write the six `F03_*.py` files
(Decision A: one smoke per spec section,
`F03_01_event_filtering.py` … `F03_06_acceptance.py`).
