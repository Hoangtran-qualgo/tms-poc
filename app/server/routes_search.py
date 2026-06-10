"""Search route (JSON API)."""

from __future__ import annotations

from flask import jsonify, request

from ._shared import api, _storage


@api.get("/search")
def search():
    q = request.args.get("q", "")
    scope = request.args.get("scope", "all")
    match = request.args.get("match", "text")
    case_sensitive = request.args.get("case", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    hits = _storage().search(
        q, scope=scope, match=match, case_sensitive=case_sensitive
    )
    return jsonify({"hits": hits})
