"""Runs-list (group view) status badges use the canonical [data-status]
palette, not divergent hard-coded tints.

Pins the "Test-run list: status badge colours match the result palette" item
(IN-PROGRESS Must-have, Jun 16 2026): each badge carries a data-status (so
app.css colours it like the run editor's chips + the result <select>) and
shows symbol + count ONLY (no status word). The old divergent tints
(PENDING slate-200, EXECUTING amber, SKIPPED slate-100) are gone.
"""
import tempfile, pathlib, re
from app import create_app
from app.storage import Storage
from app.models import RunResult

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.import_test_run(
        project="Alpha", group="release-1", name="Sprint A",
        file_name="sprint-a", created_at="2026-06-16T10:00:00+00:00",
        results=[
            RunResult(file_path="Alpha/Checkout/a.feature", result="PASSED"),
            RunResult(file_path="Alpha/Checkout/b.feature", result="FAILED"),
            RunResult(file_path="Alpha/Checkout/c.feature", result="PENDING"),
            RunResult(file_path="Alpha/Checkout/d.feature", result="EXECUTING"),
            RunResult(file_path="Alpha/Checkout/e.feature", result="SKIPPED"),
        ],
    )
    html = app.test_client().get(
        "/ui/folder/Alpha/test-run/release-1"
    ).get_data(as_text=True)

    # Each present status badge carries a data-status hook (app.css colours it).
    for status in ("PASSED", "FAILED", "PENDING", "EXECUTING", "SKIPPED"):
        assert f'data-status="{status}"' in html, f"{status} badge must carry data-status"
    print("PASS group-view badges carry data-status (canonical palette)")

    # No badge carries a hard-coded bg-* tint — colour comes from data-status.
    for status in ("PASSED", "FAILED", "PENDING", "EXECUTING", "SKIPPED"):
        m = re.search(r'<span class="([^"]*)" data-status="%s"' % status, html)
        assert m, f"{status} badge span not found"
        assert "bg-" not in m.group(1), (
            f"{status} badge must not hard-code a bg tint: {m.group(1)!r}"
        )
    print("PASS no badge hard-codes a bg tint (palette via data-status)")

    # Symbol + count only — no status word in the badges.
    for word in ("PASSED", "FAILED", "PENDING", "EXECUTING", "SKIPPED"):
        assert f"{word}</span>" not in html, f"list badge must NOT show the {word} word"
    assert "&#10003; 1" in html or "\u2713 1" in html, "PASSED symbol + count expected"
    print("PASS badges show symbol + count only (no status word)")
