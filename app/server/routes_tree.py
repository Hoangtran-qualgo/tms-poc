"""Tree + events (SSE) routes."""

from __future__ import annotations

from flask import Response, jsonify

from ..sse import sse_response
from ._shared import api, _bus, _storage


@api.get("/tree")
def get_tree() -> Response:
    return jsonify(_storage().list_tree())


@api.get("/events")
def get_events() -> Response:
    return sse_response(_bus())
