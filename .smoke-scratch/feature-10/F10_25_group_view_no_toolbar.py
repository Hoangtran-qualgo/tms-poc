"""Smoke 2a: group view no longer renders a `+ New run` toolbar button.

Reaches the populated branch of folder_test_run_group.html (at least
one run in the group) and verifies the previously-present toolbar
button is gone. The button now lives only in the Test-run sidebar tab.
"""
import re, tempfile, pathlib
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha" / "test-run" / "smoke").mkdir(parents=True)
    (d / "alpha" / "test-run" / "smoke" / "first.yaml").write_text(
        "name: First\ncreated_at: '2026-06-08T00:00:00+00:00'\ndescription: ''\nresults: []\n"
    )

    app = create_app(data_root=d)
    html = app.test_client().get("/ui/folder/alpha/test-run/smoke").get_data(
        as_text=True
    )

    # No tmsCreateRun call anywhere in the group view.
    assert "tmsCreateRun" not in html, "tmsCreateRun unexpectedly present"
    # No "+ New run" or "+ Create the first run" button labels either.
    assert not re.search(r"\+\s*New run", html), "stale '+ New run' label"
    assert not re.search(r"\+\s*Create the first run", html), "stale CTA label"
    print("PASS  group view (populated) has no run-creation affordance")


if __name__ == "__main__":
    main()
