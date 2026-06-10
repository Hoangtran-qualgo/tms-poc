"""Test-run routes (typed area under ``<project>/test-run/``).

See specs/features/10-feature-test-run-NEW.md for the design. All routes
below sit alongside the existing /api/* surface and return the same
{error: {code, message, details}} envelope on failure.
"""

from __future__ import annotations

from urllib.parse import unquote

from flask import jsonify

from ..models import TestRun
from ._shared import (
    api,
    _require_json_object,
    _require_list_of_str,
    _require_non_empty_string,
    _require_optional_str,
    _storage,
)


@api.get("/run-groups")
def get_run_groups():
    """Return all projects + the flat list of existing run groups.

    Used by the sidebar's "+ New run" modal (``tmsCreateRun`` in
    ``app/static/app.js``) to populate two surfaces from a single
    fetch:

    - the path ``<select>`` with one ``<optgroup label="proj">`` per
      project that already has groups, plus the trailing
      ``+ Create new group...`` row;
    - the project ``<select>`` shown only when the user picks
      ``+ Create new group...``, which lists every existing project
      (regardless of whether it has a ``test-run/`` folder yet).

    Shape::

        {
          "projects": ["proj-a", "proj-b", ...],
          "groups":   [
            {"project": "proj-a", "group": "smoke"},
            {"project": "proj-a", "group": "regression"},
            ...
          ]
        }

    Projects without a ``test-run/`` folder appear in ``projects``
    but contribute zero rows to ``groups`` (the area is lazy-created
    by :meth:`Storage.create_run_group` on the next POST).
    ``projects`` is sorted case-insensitively; ``groups`` follows the
    project-then-group order returned by :meth:`Storage.list_test_run_tree`.
    """
    s = _storage()
    groups: list[dict[str, str]] = []
    tree = s.list_test_run_tree()
    for project_node in tree.get("children", []):
        project = project_node["name"]
        for group_node in project_node.get("children", []):
            groups.append({"project": project, "group": group_node["name"]})
    return jsonify({"projects": s.list_projects(), "groups": groups})


@api.post("/runs/<project>/groups")
def post_run_group(project: str):
    body = _require_json_object()
    name = _require_non_empty_string(body.get("name"), "name")
    _storage().create_run_group(project, name)
    return jsonify({"ok": True}), 201


@api.delete("/runs/<project>/groups/<group>")
def delete_run_group(project: str, group: str):
    _storage().delete_run_group(project, group)
    return "", 204


@api.post("/runs")
def post_run():
    body = _require_json_object()
    project = _require_non_empty_string(body.get("project"), "project")
    group = _require_non_empty_string(body.get("group"), "group")
    name = _require_non_empty_string(body.get("name"), "name")
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    case_paths = _require_list_of_str(body.get("case_paths", []), "case_paths")
    description = _require_optional_str(body.get("description"), "description")
    _storage().create_run(
        project=project,
        group=group,
        name=name,
        file_name=file_name,
        case_paths=case_paths,
        description=description,
    )
    return jsonify({"ok": True}), 201


@api.get("/runs/<project>/<group>")
def get_run_list(project: str, group: str):
    return jsonify({"runs": _storage().list_runs(project, group)})


@api.get("/runs/<project>/<group>/<file_name>")
def get_run(project: str, group: str, file_name: str):
    run = _storage().read_run(project, group, file_name)
    return jsonify(run.to_dict())


@api.patch("/runs/<project>/<group>/<file_name>")
def patch_run(project: str, group: str, file_name: str):
    body = _require_json_object()
    run = TestRun.from_dict(body)
    _storage().write_run(project, group, file_name, run)
    return jsonify({"ok": True})


@api.delete("/runs/<project>/<group>/<file_name>")
def delete_run(project: str, group: str, file_name: str):
    _storage().delete_run(project, group, file_name)
    return "", 204


@api.post("/runs/<project>/<group>/<file_name>/cases")
def post_run_case(project: str, group: str, file_name: str):
    body = _require_json_object()
    case_path = _require_non_empty_string(body.get("file_path"), "file_path")
    _storage().add_run_case(project, group, file_name, case_path)
    return jsonify({"ok": True}), 201


@api.delete("/runs/<project>/<group>/<file_name>/cases/<path:case_path>")
def delete_run_case(
    project: str, group: str, file_name: str, case_path: str
):
    _storage().remove_run_case(
        project, group, file_name, unquote(case_path)
    )
    return "", 204


@api.patch("/runs/<project>/<group>/<file_name>/cases/<path:case_path>")
def patch_run_case(
    project: str, group: str, file_name: str, case_path: str
):
    body = _require_json_object()
    result = body.get("result")
    remark = body.get("remark")
    if result is not None and not isinstance(result, str):
        raise ValueError("Body field 'result' must be a string if present.")
    if remark is not None and not isinstance(remark, str):
        raise ValueError("Body field 'remark' must be a string if present.")
    _storage().update_run_result(
        project,
        group,
        file_name,
        unquote(case_path),
        result=result,
        remark=remark,
    )
    return jsonify({"ok": True})


@api.get("/runs/<project>")
def get_project_runs(project: str):
    """Return a flat list of every run in ``<project>``, newest first.

    Backs the report run-picker (``tmsBuildRunPicker`` in ``app.js``).
    Each entry is ``{path, group, file_name, name, created_at}`` where
    ``path`` is the data-root-relative run path a report stores in its
    ``run_paths``. Empty list if the project has no ``test-run/`` folder.
    """
    s = _storage()
    out: list[dict[str, str]] = []
    for group in s.list_run_groups(project):
        for run in s.list_runs(project, group):
            out.append(
                {
                    "path": f"{project}/test-run/{group}/{run['file_name']}",
                    "group": group,
                    "file_name": run["file_name"],
                    "name": run["name"],
                    "created_at": run["created_at"],
                }
            )
    out.sort(key=lambda r: r["path"])
    out.sort(key=lambda r: r["created_at"] or "", reverse=True)
    return jsonify({"runs": out})
