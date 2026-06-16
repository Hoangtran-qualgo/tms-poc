"""3.F (spec smoke 3.d) — Tombstone rendering for missing case files.

Verifies:
  1. A row whose underlying .feature was deleted renders with the
     'run-row-missing' class, line-through link, and a
     "file has been removed" note under the filename (tech-09 DQ1).
  2. The remark <textarea> is still present in the DOM (hidden), so
     the stored remark survives any subsequent Save round-trip.
  3. Sibling rows whose files still exist are unaffected.
  4. Restoring the file un-tombstones the row on the next render.
  5. The stored YAML is unchanged by tombstone rendering — the
     storage layer never auto-mutates runs whose cases vanish.
"""
import json
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
    # create_run only records paths in YAML; we must actually create the
    # .feature files so the tombstone check distinguishes present from
    # missing files.
    s.create_file(["Alpha", "Checkout", "pay"], description="pay")
    s.create_file(["Alpha", "Checkout", "refund"], description="refund")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/pay.feature", "Alpha/Checkout/refund.feature"],
    )
    # Give the soon-to-be-deleted row a non-trivial remark so we can
    # assert it round-trips.
    s.update_run_result(
        project="Alpha", group="release-1", file_name="smoke.yaml",
        case_path="Alpha/Checkout/pay.feature",
        result="FAILED", remark="green before deletion",
    )

    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    bytes_before = yaml_path.read_bytes()

    # Delete the underlying .feature file (the storage layer never
    # auto-mutates the run; this is the orphan-case scenario).
    (root / "Alpha" / "Checkout" / "pay.feature").unlink()

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)

    # 1) The deleted row carries the tombstone marker class + data-missing.
    pay_row = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/pay\.feature"[^>]*>(.*?)</tr>',
        html, re.S,
    )
    assert pay_row, "deleted-case row missing"
    pay_tr_open = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/pay\.feature"[^>]*>',
        html,
    ).group(0)
    assert "run-row-missing" in pay_tr_open, pay_tr_open
    assert 'data-missing="1"' in pay_tr_open, pay_tr_open
    # Strike-through styling applied to the file_path link.
    assert "line-through" in pay_row.group(1), "missing line-through on tombstone link"
    # Removed-case note visible under the filename (tech-09 DQ1).
    assert "file has been removed" in pay_row.group(1), "removed note missing"
    assert "run-removed-note" in pay_row.group(1), "removed-note element missing"
    # The textarea is still in the DOM, but hidden, and still carries
    # the stored remark (round-trip preserved).
    ta_match = re.search(
        r'<textarea class="run-remark[^"]*"[^>]*>([^<]*)</textarea>',
        pay_row.group(1),
    )
    assert ta_match, "remark textarea missing from tombstoned row"
    assert "hidden" in ta_match.group(0).split('class="')[1].split('"')[0].split(), (
        "tombstoned remark textarea should carry the hidden class"
    )
    assert ta_match.group(1) == "green before deletion", ta_match.group(1)
    print("PASS 3.F deleted case renders as tombstone w/ preserved remark")

    # 2) Sibling row (file still exists) is unaffected.
    refund_row = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/refund\.feature"[^>]*>(.*?)</tr>',
        html, re.S,
    )
    assert refund_row, "sibling row missing"
    refund_tr_open = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/refund\.feature"[^>]*>',
        html,
    ).group(0)
    assert "run-row-missing" not in refund_tr_open
    assert "data-missing" not in refund_tr_open
    assert "line-through" not in refund_row.group(1)
    assert "file has been removed" not in refund_row.group(1)
    print("PASS 3.F sibling rows with present files are unaffected")

    # 3) The on-disk YAML is not auto-mutated by render.
    assert yaml_path.read_bytes() == bytes_before, "render must not touch the YAML"
    print("PASS 3.F render does not mutate stored YAML")

    # 4) Restore the file → next render un-tombstones.
    (root / "Alpha" / "Checkout" / "pay.feature").write_text(
        "Feature: pay\n  Scenario: x\n    Given a step\n"
    )
    html2 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    pay_tr2 = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/pay\.feature"[^>]*>',
        html2,
    ).group(0)
    assert "run-row-missing" not in pay_tr2
    assert "data-missing" not in pay_tr2
    pay_row2 = re.search(
        r'<tr[^>]*data-file-path="Alpha/Checkout/pay\.feature"[^>]*>(.*?)</tr>',
        html2, re.S,
    )
    assert "file has been removed" not in pay_row2.group(1)
    print("PASS 3.F restoring the file un-tombstones the row on next render")

    # 5) Save a tombstoned editor: the PATCH payload (built as the
    # client would) preserves the stored remark + result through the
    # round-trip even while tombstoned.
    initial = s.read_run("Alpha", "release-1", "smoke.yaml").to_dict()
    # Simulate the client re-deleting the file and Save firing.
    (root / "Alpha" / "Checkout" / "pay.feature").unlink()
    payload = {
        "name": initial["name"],
        "created_at": initial["created_at"],
        "description": initial["description"],
        "results": initial["results"],  # value pulled from the hidden textarea
    }
    r = client.patch(
        "/api/runs/Alpha/release-1/smoke.yaml",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    persisted = s.read_run("Alpha", "release-1", "smoke.yaml").to_dict()
    pay = next(rr for rr in persisted["results"]
               if rr["file_path"] == "Alpha/Checkout/pay.feature")
    assert pay["result"] == "FAILED" and pay["remark"] == "green before deletion", pay
    print("PASS 3.F Save round-trip preserves remark + result on a tombstoned row")
