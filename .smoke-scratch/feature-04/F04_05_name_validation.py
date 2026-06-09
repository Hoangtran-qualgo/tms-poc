# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / Name validation (NV1).

Route-layer assertion; the storage-half of NV1 (per-segment validation
in `_validate_segment`) lives in feature-02's F02_01_path_discipline.py.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- NV1: every segment passes _validate_segment at the route layer ----
    # Forbidden character set per spec: / \ : * ? " < > | + control chars.
    # Also empty / "." / ".." are rejected.

    # 1. Empty name -> caught early by _require_non_empty_string.
    r = client.post("/api/folders", json={"parent": "", "name": ""})
    assert r.status_code == 400, (
        f"NV1: empty name must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request", (
        "NV1: empty name must carry error.code='bad_request'"
    )

    # 2. Each forbidden character as the leaf name.
    forbidden = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in forbidden:
        name = f"a{ch}b"
        r = client.post("/api/folders", json={"parent": "", "name": name})
        assert r.status_code == 400, (
            f"NV1: forbidden char {ch!r} in name must return 400, got {r.status_code}"
        )
        body = r.get_json()
        assert body and body.get("error", {}).get("code") == "bad_request", (
            f"NV1: forbidden char {ch!r} must carry error.code='bad_request', got {body!r}"
        )
        assert not (root / name).exists(), (
            f"NV1: folder with forbidden char {ch!r} must NOT be created on disk"
        )

    # 3. Control characters (NUL, BEL, newline, tab).
    for ch in ['\x00', '\x07', '\n', '\t', '\x1f']:
        name = f"x{ch}y"
        r = client.post("/api/folders", json={"parent": "", "name": name})
        assert r.status_code == 400, (
            f"NV1: control char {ch!r} (ord {ord(ch)}) must return 400, got {r.status_code}"
        )
        assert r.get_json()["error"]["code"] == "bad_request", (
            f"NV1: control char {ch!r} must carry error.code='bad_request'"
        )

    # 4. The "." and ".." sentinels.
    for name in [".", ".."]:
        r = client.post("/api/folders", json={"parent": "", "name": name})
        assert r.status_code == 400, (
            f"NV1: sentinel name {name!r} must return 400, got {r.status_code}"
        )
        assert r.get_json()["error"]["code"] == "bad_request", (
            f"NV1: sentinel name {name!r} must carry error.code='bad_request'"
        )

    # 5. Forbidden char in PARENT segment (not just leaf) is also rejected.
    r = client.post("/api/folders", json={"parent": "good/bad:seg", "name": "leaf"})
    assert r.status_code == 400, (
        f"NV1: forbidden char in PARENT segment must return 400, got {r.status_code}"
    )

    # 6. A clean name confirms the validator is not a global reject.
    r = client.post("/api/folders", json={"name": "ValidName_123"})
    assert r.status_code == 201, (
        f"NV1 sanity: clean name 'ValidName_123' must succeed (201), got {r.status_code}"
    )
print(
    "PASS  NV1: forbidden chars / control chars / empty / '.' / '..' -> 400 with "
    "error.code='bad_request'; clean names accepted"
)
