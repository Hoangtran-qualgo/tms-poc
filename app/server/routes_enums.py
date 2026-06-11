"""Project-level enums routes (``<project>/enums.yaml``).

See specs/features/11-feature-testcase-component-NEW.md. Routes are
named under /api/enums/<project> to match the project-scoped convention
established by /api/runs/<project>/groups.
"""

from __future__ import annotations

from flask import jsonify, request

from ._shared import api, _require_json_object, _require_non_empty_string, _storage


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


@api.put("/enums/<project>")
def put_project_enums(project: str):
    """Replace ``<project>/enums.yaml`` with the posted whole-document vocab.

    Body is the ``{kind: {key: label}}`` map. Returns the freshly-parsed
    dict on success. 404 if the project / file is missing (Initialize
    first); 422 ``enums_parse_error`` on a schema-invalid payload; 409
    ``enum_in_use`` if the edit would drop a key/kind that a ``.feature``
    still references.
    """
    body = _require_json_object()
    return jsonify(_storage().write_project_enums(project, body))


@api.post("/enums/<project>/rename")
def post_project_enum_rename(project: str):
    """Rename ``kind.old_key`` to ``new_key`` with a cascade across features.

    Body: ``{kind, old_key, new_key}``. Returns ``{renamed: <count>}`` (the
    number of ``.feature`` files rewritten). 404 if the project / file is
    missing; 422 ``validation_error`` for an unknown kind/key or an invalid
    ``new_key``; 422 ``parse_error`` if a feature fails the dry-run parse;
    409 ``name_conflict`` if ``new_key`` already exists in the kind.
    """
    body = _require_json_object()
    kind = _require_non_empty_string(body.get("kind"), "kind")
    old_key = _require_non_empty_string(body.get("old_key"), "old_key")
    new_key = _require_non_empty_string(body.get("new_key"), "new_key")
    renamed = _storage().rename_enum_key(project, kind, old_key, new_key)
    return jsonify({"renamed": renamed})


@api.post("/enums/<project>/clear")
def post_project_enums_clear(project: str):
    """Reset ``<project>/enums.yaml`` to the default seed (fresh start, D11).

    Returns ``{cleared: true}`` on success. 404 if the project / file is
    missing; 409 ``enum_in_use`` (with the in-use enum + referencing case in
    the details/message) if any case still references the vocabulary — the
    user must clear that enum in the test case first.
    """
    _storage().clear_project_enums(project)
    return jsonify({"cleared": True})


@api.get("/enums/<project>/usage")
def get_project_enum_usage(project: str):
    """Return ``{count, sample}`` for a ``kind``/``key`` query parameter pair.

    Backs the manager's remove / rename / clear preview. 404 if the
    project / file is missing; 400 if ``kind`` or ``key`` is absent.
    """
    kind = _require_non_empty_string(request.args.get("kind"), "kind")
    key = _require_non_empty_string(request.args.get("key"), "key")
    # Surface a 404 for a legacy project the same way the other routes do.
    _storage().read_project_enums(project)
    count, sample = _storage().count_enum_key_usage(project, kind, key)
    return jsonify({"count": count, "sample": sample})
