"""3.E — run_editor.html always renders the results table + empty state,
and exposes a <template id="run-result-row-template"> prototype with
all RUN_RESULTS options so the controller can clone new rows without
duplicating that list in JS."""
import re
import tempfile, pathlib
from app import create_app
from app.models import RUN_RESULTS
from app.storage import Storage

# Case 1: empty run — table is rendered with `hidden` class, empty
# state is visible, prototype <template> exists with full option list.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    # Empty run — need to construct via PATCH after creating with one
    # case + removing it, OR create with a placeholder. We use a tiny
    # case_paths=[<existing>] and never reference it; an empty run is
    # also valid per the dataclass invariants but create_run wants
    # case_paths to be non-empty? Let me check by writing directly.
    s.create_folder(["Alpha", "Checkout"])
    s.create_run(
        project="Alpha", group="release-1", name="Empty test", file_name="empty",
        case_paths=["Alpha/Checkout/temp.feature"],
    )
    # Remove the case to leave an empty run.
    s.remove_run_case("Alpha", "release-1", "empty.yaml",
                     "Alpha/Checkout/temp.feature")

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/empty.yaml").get_data(as_text=True)

    # Both table and empty-state are present, with hidden flipped.
    assert 'id="run-results"' in html
    assert 'id="run-results-empty"' in html
    def _has_hidden(cls_str):
        return "hidden" in cls_str.split()
    table_re = re.search(r'<table id="run-results"[^>]*class="([^"]+)"', html)
    empty_re = re.search(r'id="run-results-empty"[^>]*class="([^"]+)"', html)
    assert table_re and _has_hidden(table_re.group(1)), table_re
    assert empty_re and not _has_hidden(empty_re.group(1)), empty_re
    print("PASS 3.E empty run: table hidden, empty-state visible")

    # Prototype row template carries all RUN_RESULTS options.
    tpl_re = re.search(
        r'<template id="run-result-row-template">(.*?)</template>',
        html, re.S,
    )
    assert tpl_re, "row prototype <template> missing"
    tpl_body = tpl_re.group(1)
    for cls in ("run-row-link", "run-result-select", "run-remark", "run-row-remove"):
        assert cls in tpl_body, f"prototype missing class: {cls}"
    for opt in RUN_RESULTS:
        assert f'value="{opt}"' in tpl_body, f"option {opt} missing from prototype"
    print("PASS 3.E prototype row carries all RUN_RESULTS options")

# Case 2: non-empty run — table is visible, empty state is hidden.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="One",
                 file_name="one", case_paths=["Alpha/Checkout/a.feature"])

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/one.yaml").get_data(as_text=True)
    def _has_hidden(cls_str):
        return "hidden" in cls_str.split()
    table_re = re.search(r'<table id="run-results"[^>]*class="([^"]+)"', html)
    empty_re = re.search(r'id="run-results-empty"[^>]*class="([^"]+)"', html)
    assert table_re and not _has_hidden(table_re.group(1)), table_re.group(1)
    assert empty_re and _has_hidden(empty_re.group(1)), empty_re.group(1)
    print("PASS 3.E non-empty run: table visible, empty-state hidden")
