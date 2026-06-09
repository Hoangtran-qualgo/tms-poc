"""Smoke 1a: Test-run sidebar renders a `+ New run` button.

Renders the sidebar partial in three states (no data; data with runs;
data with a bare project) and verifies the button is present in every
state. Confirms the "always visible" promise from the agreed direction.
"""
import re, tempfile, pathlib
from app import create_app


def _has_new_run_button(html: str) -> bool:
    # The exact button text is "+ New run". Tolerate surrounding tags
    # but anchor on the slate-800 button class to avoid matching other
    # affordances that may use the same label later.
    return bool(
        re.search(
            r"<button[^>]*onclick=\"tmsCreateRun\(\)\"[^>]*>\s*\+ New run\s*</button>",
            html,
        )
    )


def _render(d: pathlib.Path) -> str:
    app = create_app(data_root=d)
    r = app.test_client().get("/ui/test-run-tree")
    assert r.status_code == 200, r.status_code
    return r.get_data(as_text=True)


def main() -> None:
    # Empty data root.
    html = _render(pathlib.Path(tempfile.mkdtemp()))
    assert _has_new_run_button(html), "missing button in empty-root state"
    print("PASS  button present when data root is empty")

    # Bare project (no test-run/).
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha").mkdir()
    assert _has_new_run_button(_render(d)), "missing button with bare project"
    print("PASS  button present when project has no test-run/")

    # Project with one run.
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha" / "test-run" / "smoke").mkdir(parents=True)
    (d / "alpha" / "test-run" / "smoke" / "first.yaml").write_text(
        "name: First\ncreated_at: '2026-06-08T00:00:00+00:00'\ndescription: ''\nresults: []\n"
    )
    assert _has_new_run_button(_render(d)), "missing button when runs exist"
    print("PASS  button present when at least one run exists")


if __name__ == "__main__":
    main()
