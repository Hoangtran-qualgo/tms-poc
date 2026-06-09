"""Smoke 5: POST /api/runs/<project>/groups twice with the same name → 409.

Run-group name uniqueness within project is enforced by
Storage.create_run_group raising NameConflictError on a pre-existing
folder; the error handler maps that to HTTP 409. The modal's submit
handler surfaces this as an inline error under the group-name input,
keeping the user's run-name + project selection intact.

Verifies the contract end-to-end: second POST returns 409, the message
contains "already exists" (the substring the JS submit handler's regex
matches to render the friendly inline copy), and the storage side has
not double-written anything.
"""
import tempfile, pathlib, json, re
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha").mkdir()
    app = create_app(data_root=d)
    c = app.test_client()

    r1 = c.post(
        "/api/runs/alpha/groups",
        data=json.dumps({"name": "smoke"}),
        content_type="application/json",
    )
    assert r1.status_code == 201, r1.status_code
    print("PASS  first POST returns 201")

    r2 = c.post(
        "/api/runs/alpha/groups",
        data=json.dumps({"name": "smoke"}),
        content_type="application/json",
    )
    assert r2.status_code == 409, (r2.status_code, r2.get_data(as_text=True))
    print("PASS  duplicate POST returns 409")

    body = r2.get_json()
    # The blueprint wraps errors as {error: {message: "...", ...}}; the
    # JS submit handler reads `e.message` which `tmsApiPost` sets from
    # `error.message`. The substring the JS regex matches is "already
    # exists".
    msg = (body or {}).get("error", {}).get("message", "")
    assert re.search(r"already exists", msg, re.I), msg
    print("PASS  409 body carries 'already exists' message")

    # The single group folder still exists exactly once; no duplicate
    # writes despite the second POST.
    children = sorted(p.name for p in (d / "alpha" / "test-run").iterdir())
    assert children == ["smoke"], children
    print("PASS  group folder exists exactly once on disk")


if __name__ == "__main__":
    main()
