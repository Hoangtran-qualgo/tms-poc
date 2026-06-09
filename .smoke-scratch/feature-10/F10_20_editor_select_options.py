"""3.C — Every result <select> in the run editor lists all RUN_RESULTS
options, with the stored value pre-selected."""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.models import RUN_RESULTS

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke",
        file_name="smoke", case_paths=["Alpha/Checkout/a.feature"],
    )
    s.update_run_result(
        project="Alpha", group="release-1", file_name="smoke.yaml",
        case_path="Alpha/Checkout/a.feature",
        result="SKIPPED", remark="env down",
    )

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)

    # Isolate the single select block
    m = re.search(r'<select class="run-result-select[^>]*>(.*?)</select>', html, re.S)
    assert m, "result <select> missing"
    options_block = m.group(1)

    # All RUN_RESULTS options listed, in order, each as an <option>
    for opt in RUN_RESULTS:
        assert f'value="{opt}"' in options_block, f"missing option {opt}"

    # The stored value (BLOCKED) is the one with `selected`
    sel_match = re.search(r'<option value="([^"]+)"\s+selected>', options_block)
    assert sel_match and sel_match.group(1) == "SKIPPED", sel_match
    print("PASS 3.C select renders all RUN_RESULTS with stored value pre-selected")
