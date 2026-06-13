"""tech-05 SN1/SN3/RD-4 — run editor renders a display-only Scenario name.

Verifies (spec `specs/tech/05-tech-run-detail-scenario-name-NEW.md`):
  1. The results table has a `Scenario name` header column.
  2. `ui_run` attaches each result's scenario name read LIVE from the
     `.feature` (a plain `run-scenario-name` <td>, NOT an input).
  3. It is read live, not snapshotted: editing the case's scenario name
     and re-rendering reflects the new value without touching the run YAML.
  4. RD-4: a tombstoned / unreadable case renders a blank scenario name.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "pay"], scenario_name="User pays with card")
    s.create_file(["Alpha", "Checkout", "refund"], scenario_name="User requests refund")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/pay.feature", "Alpha/Checkout/refund.feature"],
    )

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)

    # 1) Header column present (between Test case and Result is not asserted
    #    structurally here; the column merely has to exist).
    assert re.search(r"<th[^>]*>\s*Scenario name\s*</th>", html), "Scenario name header missing"
    print("PASS SN1 results table has a Scenario name header")

    def scenario_cell(row_html):
        return re.search(
            r'<td class="run-scenario-name[^"]*"[^>]*>(.*?)</td>', row_html, re.S
        )

    def row_of(path, doc):
        return re.search(
            rf'<tr[^>]*data-file-path="{re.escape(path)}"[^>]*>(.*?)</tr>', doc, re.S
        )

    pay_row = row_of("Alpha/Checkout/pay.feature", html)
    assert pay_row, "pay row missing"
    cell = scenario_cell(pay_row.group(1))
    assert cell, "pay scenario-name cell missing"
    # 2) Live scenario name rendered as plain text (no nested form control).
    assert "User pays with card" in cell.group(1), cell.group(1)
    assert not re.search(r"<(input|select|textarea)", cell.group(1)), (
        "scenario name must be display-only text, not an input"
    )
    print("PASS SN1 scenario name rendered live as a display-only cell")

    # 3) Read live, not snapshotted: rewrite the case's scenario name then
    #    re-render. The run YAML is untouched; the cell reflects the new name.
    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    bytes_before = yaml_path.read_bytes()
    s.write_raw(
        "Alpha/Checkout/pay.feature",
        "Feature: pay\n  Scenario: Customer pays via wallet\n    Given a step\n",
    )
    html2 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    cell2 = scenario_cell(row_of("Alpha/Checkout/pay.feature", html2).group(1))
    assert "Customer pays via wallet" in cell2.group(1), cell2.group(1)
    assert yaml_path.read_bytes() == bytes_before, "render must not mutate the run YAML"
    print("PASS SN3 scenario name is read live (not snapshotted into the run)")

    # 4) RD-4: tombstoned / unreadable case → blank scenario name.
    (root / "Alpha" / "Checkout" / "refund.feature").unlink()
    html3 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    refund_cell = scenario_cell(row_of("Alpha/Checkout/refund.feature", html3).group(1))
    assert refund_cell, "refund scenario-name cell missing"
    assert refund_cell.group(1).strip() == "", (
        f"tombstoned case must have a blank scenario name, got {refund_cell.group(1)!r}"
    )
    print("PASS RD-4 tombstoned / unreadable case renders a blank scenario name")
