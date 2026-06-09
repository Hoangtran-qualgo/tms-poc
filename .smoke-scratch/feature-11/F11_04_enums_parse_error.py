"""S2.1 smoke — EnumsParseError maps to 422 enums_parse_error envelope.

Mounts a one-shot test route on the `api` blueprint that raises an
EnumsParseError; verifies the registered handler produces:

  status 422, JSON { error: { code: 'enums_parse_error', message, details:
                              { line, column } } }.
"""
import json
import pathlib
import tempfile

from app import create_app
from app.errors import EnumsParseError
from app.server import api


# Register a probe route ONCE at import time (the blueprint binds to the
# app only when create_app() is called below).
@api.get("/_probe_enums_parse_error")
def _probe():
    raise EnumsParseError(line=7, column=3, message="probe failure")


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    r = client.get("/api/_probe_enums_parse_error")
    assert r.status_code == 422, r.status_code
    body = r.get_json()
    assert body == {
        "error": {
            "code": "enums_parse_error",
            "message": "probe failure",
            "details": {"line": 7, "column": 3},
        }
    }, json.dumps(body)
    print("PASS  EnumsParseError maps to 422 enums_parse_error envelope")
