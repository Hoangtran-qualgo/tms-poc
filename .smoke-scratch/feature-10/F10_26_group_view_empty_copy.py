"""Smoke 2b: empty group view shows pointer copy, not a CTA button.

Reaches the empty branch of folder_test_run_group.html (group exists
but has zero runs) and verifies:
- the previous `+ Create the first run` CTA button is gone;
- a pointer copy mentions the Test-run sidebar tab so cold-start
  users can find the affordance.
"""
import re, tempfile, pathlib
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha" / "test-run" / "smoke").mkdir(parents=True)  # group exists, no runs

    app = create_app(data_root=d)
    html = app.test_client().get("/ui/folder/alpha/test-run/smoke").get_data(
        as_text=True
    )

    assert "tmsCreateRun" not in html, "tmsCreateRun unexpectedly present"
    assert not re.search(r"\+\s*Create the first run", html), "stale CTA label"
    print("PASS  empty state has no CTA button")

    # Pointer copy must mention "Test run" sidebar tab in the empty state.
    assert "No runs yet" in html, html
    assert re.search(r"Test\s*run", html), "missing pointer to sidebar tab"
    assert "sidebar tab" in html.lower(), "missing 'sidebar tab' phrasing"
    print("PASS  empty state points users at the Test run sidebar tab")


if __name__ == "__main__":
    main()
