"""Project-level enums routes (``<project>/enums.yaml``).

See specs/features/11-feature-testcase-component-NEW.md. Routes are
named under /api/enums/<project> to match the project-scoped convention
established by /api/runs/<project>/groups.
"""

from __future__ import annotations

from flask import jsonify

from ._shared import api, _storage


@api.get("/enums/<project>")
def get_project_enums(project: str):
    """Return the parsed ``<project>/enums.yaml`` as ``{kind: {key: label}}``.

    404 if the file is missing (legacy project); 422 ``enums_parse_error``
    if the file is malformed or schema-invalid (mapped from
    :class:`~app.errors.EnumsParseError`).
    """
    return jsonify(_storage().read_project_enums(project))


@api.post("/enums/<project>")
def post_project_enums_init(project: str):
    """Initialise ``<project>/enums.yaml`` with the default ``components:`` seed.

    201 with the freshly-parsed dict body on success; 409 ``name_conflict``
    if the file already exists (no overwrite); 404 if the project folder
    is missing.
    """
    return jsonify(_storage().init_project_enums(project)), 201
