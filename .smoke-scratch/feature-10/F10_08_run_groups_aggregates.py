"""Smoke 3c: GET /api/run-groups aggregates groups across projects.

Two projects, one with two existing groups and one bare. Verifies:
- ``projects`` is sorted case-insensitively (so the optgroup ordering
  in the modal is stable);
- ``groups`` lists every (project, group) pair as a flat dict;
- bare projects (no test-run/) still appear in ``projects`` and
  contribute zero rows to ``groups``.
"""
import tempfile, pathlib
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "kchatb2b").mkdir()                       # bare
    (d / "alpha").mkdir()                          # with groups
    (d / "alpha" / "test-run").mkdir()
    (d / "alpha" / "test-run" / "smoke").mkdir()
    (d / "alpha" / "test-run" / "regression").mkdir()

    app = create_app(data_root=d)
    body = app.test_client().get("/api/run-groups").get_json()

    assert body["projects"] == ["alpha", "kchatb2b"], body["projects"]
    print("PASS  projects sorted case-insensitive (bare project included)")

    pairs = {(g["project"], g["group"]) for g in body["groups"]}
    assert pairs == {("alpha", "smoke"), ("alpha", "regression")}, pairs
    assert len(body["groups"]) == 2, body["groups"]
    print("PASS  groups flat list contains exactly the two existing pairs")


if __name__ == "__main__":
    main()
