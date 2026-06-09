# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / SF2 -- scope='project:<name>'.

SF2: scope='project:<name>' restricts to files whose FIRST path segment
     is <name>, across all of that project's modules.

Re-owns the project-scope branch end-to-end through /api/search
(cross-credit: feature-02/F02_07 SR3).
"""
import pathlib
import tempfile

from app import create_app


def files(client, scope):
    h = client.get(f"/api/search?q=needle&match=text&scope={scope}").get_json()["hits"]
    return sorted(x["file_path"] for x in h)


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    for proj in ("Alpha", "Beta"):
        s.create_folder([proj])
    # Alpha has two modules, both with a match → project scope spans modules.
    s.create_folder(["Alpha", "Mod1"])
    s.create_folder(["Alpha", "Mod2"])
    s.create_folder(["Beta", "Mod1"])
    s.create_file(["Alpha", "Mod1", "a.feature"], "needle one")
    s.create_file(["Alpha", "Mod2", "b.feature"], "needle two")
    s.create_file(["Beta", "Mod1", "c.feature"], "needle three")

    # --- SF2: project:Alpha → both Alpha modules, NOT Beta. ---
    assert files(client, "project:Alpha") == [
        "Alpha/Mod1/a.feature",
        "Alpha/Mod2/b.feature",
    ], f"SF2: project:Alpha must span Alpha's modules only, got {files(client, 'project:Alpha')}"

    # --- SF2: project:Beta → only Beta. ---
    assert files(client, "project:Beta") == ["Beta/Mod1/c.feature"], (
        f"SF2: project:Beta must return only Beta's file, got {files(client, 'project:Beta')}"
    )

    # --- SF2: a non-existent project → no hits (not an error). ---
    assert files(client, "project:Ghost") == [], (
        "SF2: project:<unknown> must return [] (missing base dir → empty, not 400)"
    )

    # --- SF2: first-segment match is exact, not a prefix. ---
    # 'project:Alph' must not match the 'Alpha' project.
    assert files(client, "project:Alph") == [], (
        "SF2: project scope matches the first segment EXACTLY, not as a prefix"
    )

print("PASS  SF2: scope='project:<name>' restricts to the project's first-segment match across its modules (exact, not prefix)")
