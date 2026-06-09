"""Smoke 1b: Sidebar `+ New run` button calls `tmsCreateRun()` with no args.

The Phase-3 lock-in moves the button out of the (project, group) group
view; the sidebar lives outside any project context, so the call must
be parameterless and the modal must collect project/group itself.
Anchors on the exact onclick attribute to catch accidental future
parameterisation.
"""
import re, tempfile, pathlib
from app import create_app


def main() -> None:
    app = create_app(data_root=pathlib.Path(tempfile.mkdtemp()))
    html = app.test_client().get("/ui/test-run-tree").get_data(as_text=True)

    # Exactly one `+ New run` button, calling `tmsCreateRun()` with no args.
    matches = re.findall(r"onclick=\"tmsCreateRun\(([^)]*)\)\"", html)
    assert matches == [""], matches
    print('PASS  sidebar has exactly one tmsCreateRun() call, with no args')


if __name__ == "__main__":
    main()
