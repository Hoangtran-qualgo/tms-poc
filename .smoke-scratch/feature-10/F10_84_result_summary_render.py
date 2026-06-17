"""Run editor: per-status result summary below the description (server render).

Pins the "Test-run detail: result summary below the description" item
(IN-PROGRESS Must-have, Jun 16 2026). The summary sits above the Results
table and shows one chip per RUN_RESULTS status; zero-count chips are hidden
and an em-dash shows when the run is empty. Symbols/colours mirror
folder_test_run_group.html.
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
            RunResult(file_path="Alpha/Checkout/d.feature", result="PENDING"),
        ],
    )
    html = app.test_client().get(
        "/ui/run/Alpha/release-1/sprint-a.yaml"
    ).get_data(as_text=True)

    assert 'id="run-result-summary"' in html, html
    # Summary precedes the Results table header (placed below the description).
    assert html.index('id="run-result-summary"') < html.index(">Results<"), (
        "result summary must render above the Results table header"
    )

    def count_for(status):
        m = re.search(
            r'data-status="%s">[^<]*<span data-role="count">(\d+)</span>' % status,
            html,
        )
        assert m, f"missing summary chip for {status}"
        return int(m.group(1))

    def cls_for(status):
        m = re.search(r'class="([^"]*)" data-status="%s"' % status, html)
        assert m, f"missing summary chip class for {status}"
        return m.group(1)

    assert count_for("PASSED") == 1, html
    assert count_for("FAILED") == 1, html
    assert count_for("PENDING") == 2, html
    assert count_for("EXECUTING") == 0, html
    assert count_for("SKIPPED") == 0, html
    print("PASS chips carry correct per-status counts")

    # Each chip shows its status word after the count (e.g. "✓ 1 PASSED").
    for word in ("PASSED", "FAILED", "PENDING", "EXECUTING", "SKIPPED"):
        assert f" {word}</span>" in html, f"chip must show the {word} label word"
    print("PASS chips include the status word label")

    # Non-zero chips are visible; zero-count chips are hidden.
    assert "hidden" not in cls_for("PASSED"), cls_for("PASSED")
    assert "hidden" not in cls_for("PENDING"), cls_for("PENDING")
    assert "hidden" in cls_for("EXECUTING"), cls_for("EXECUTING")
    assert "hidden" in cls_for("SKIPPED"), cls_for("SKIPPED")
    # Em-dash hidden when the run has results.
    m = re.search(r'class="run-summary-empty([^"]*)"', html)
    assert m and "hidden" in m.group(1), "em-dash must be hidden when run has results"
    print("PASS zero-count chips hidden; non-zero shown; em-dash hidden")
