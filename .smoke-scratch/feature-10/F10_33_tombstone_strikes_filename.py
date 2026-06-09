"""Smoke j3: tombstone strikes the filename span only, not the folder span.

Tracks the "Investigate: run editor — mask test-case column to filename only"
Must-have item. Verifies the Q4(b) decision: when a row is tombstoned
(`r.missing`), the `line-through` class lives on the filename span only;
the folder span stays muted but unstruck. A sibling live row asserts
neither span carries `line-through` so we catch any over-eager CSS rule
that might apply line-through universally.

Mirrors the Flask test-client + Storage fixture pattern from
`F10_29_tombstone_render.py`. End-to-end render only — no JS exercised.
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
    s.create_file(["Alpha", "Checkout", "pay"], description="pay")
    s.create_file(["Alpha", "Checkout", "refund"], description="refund")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/pay.feature", "Alpha/Checkout/refund.feature"],
    )
    # Delete the underlying .feature for `pay` — that row becomes
    # tombstoned. `refund` stays live as the sibling control.
    (root / "Alpha" / "Checkout" / "pay.feature").unlink()

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)

    def row_body(file_path: str) -> str:
        m = re.search(
            rf'<tr[^>]*data-file-path="{re.escape(file_path)}"[^>]*>(.*?)</tr>',
            html, re.S,
        )
        assert m, f"row for {file_path!r} not found in rendered HTML"
        return m.group(1)

    def span(body: str, role: str) -> str:
        m = re.search(
            rf'<span[^>]*data-role="{role}"[^>]*>[^<]*</span>',
            body,
        )
        assert m, f"<span data-role='{role}'> not found in row body"
        return m.group(0)

    # --- 1. Tombstoned row: filename span struck, folder span clean ---
    pay_body = row_body("Alpha/Checkout/pay.feature")
    pay_folder = span(pay_body, "folder")
    pay_filename = span(pay_body, "filename")
    assert "line-through" in pay_filename, (
        f"tombstoned filename span should carry line-through; got: {pay_filename!r}"
    )
    assert "line-through" not in pay_folder, (
        f"tombstoned folder span should NOT carry line-through; got: {pay_folder!r}"
    )
    print("PASS  tombstoned row: filename struck, folder unstruck")

    # --- 2. Sibling live row: neither span carries line-through -------
    refund_body = row_body("Alpha/Checkout/refund.feature")
    refund_folder = span(refund_body, "folder")
    refund_filename = span(refund_body, "filename")
    assert "line-through" not in refund_folder, (
        f"live row folder span must not carry line-through; got: {refund_folder!r}"
    )
    assert "line-through" not in refund_filename, (
        f"live row filename span must not carry line-through; got: {refund_filename!r}"
    )
    print("PASS  live sibling row: neither span carries line-through")
