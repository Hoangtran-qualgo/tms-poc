# Pattern: see .smoke-scratch/README.md
"""tech-08 / test-case list revamp / storage row shape (DO-1).

`Storage.list_folder` now attaches `enums: [{kind, key, label}]` per feature
row, mirroring the report-detail enum display (tech-06 RP-2):
- selected enums resolve their human `enums.yaml` label;
- a redundant `label == key` collapses to `label == ""` (template shows the
  key alone);
- unset enums (empty-string value) are skipped;
- rows are sorted by kind;
- a file that fails to parse still lists, with `enums == []` (and `tags == []`).
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = create_app(data_root=root).extensions["storage"]
    s.create_folder(["P"])           # auto-inits enums.yaml
    s.create_folder(["P", "mod"])
    s.write_project_enums(
        "P",
        {
            "priority": {"p1": "Priority 1", "p2": "Priority 2"},
            "layer": {"api": "API"},
            "comp": {"login": "login"},  # label == key -> redundant
        },
    )

    # A case with a resolved enum, a redundant-label enum, and an unset one.
    s.create_file(["P", "mod", "a.feature"], "desc", scenario_name="A")
    feat = s.read_feature(["P", "mod", "a.feature"])
    feat.enums = {"priority": "p1", "comp": "login", "layer": ""}
    s.write_feature(["P", "mod", "a.feature"], feat)

    # A file that cannot be parsed (best-effort listing must not crash).
    (root / "P" / "mod" / "bad.feature").write_text(
        "this is not gherkin\n", encoding="utf-8"
    )

    rows = {f["file_name"]: f for f in s.list_folder(["P", "mod"])["features"]}

    # --- enum rows: kind-sorted, unset skipped, redundant label blanked -----
    assert rows["a.feature"]["enums"] == [
        {"kind": "comp", "key": "login", "label": ""},
        {"kind": "priority", "key": "p1", "label": "Priority 1"},
    ], rows["a.feature"]["enums"]

    # --- parse failure: empty enums (and empty tags), still listed ----------
    assert rows["bad.feature"]["enums"] == [], rows["bad.feature"]
    assert rows["bad.feature"]["tags"] == [], rows["bad.feature"]

print(
    "PASS  T08_01: list_folder rows carry enums [{kind,key,label}] "
    "(label resolved; redundant blanked; unset skipped; kind-sorted; "
    "parse failure -> [])"
)
