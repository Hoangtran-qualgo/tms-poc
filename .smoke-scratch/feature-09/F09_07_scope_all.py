# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / SF1 -- scope='all'.

SF1: scope='all' (the default) searches every .feature under the data
     root, regardless of project / module.

Re-owns the scope=all branch end-to-end through /api/search
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

    # Two projects, each with a matching file in different modules.
    for proj in ("Alpha", "Beta"):
        s.create_folder([proj])
    s.create_folder(["Alpha", "Mod1"])
    s.create_folder(["Beta", "Mod9"])
    s.create_file(["Alpha", "Mod1", "a.feature"], "needle in alpha")
    s.create_file(["Beta", "Mod9", "b.feature"], "needle in beta")
    s.create_file(["Alpha", "Mod1", "miss.feature"], "nothing here")

    # --- SF1: scope='all' spans both projects. ---
    assert files(client, "all") == ["Alpha/Mod1/a.feature", "Beta/Mod9/b.feature"], (
        f"SF1: scope='all' must return matches across every project, got {files(client, 'all')}"
    )

    # --- SF1: omitting scope defaults to 'all'. ---
    h = client.get("/api/search?q=needle&match=text").get_json()["hits"]
    assert sorted(x["file_path"] for x in h) == [
        "Alpha/Mod1/a.feature",
        "Beta/Mod9/b.feature",
    ], "SF1: omitting scope must behave identically to scope='all'"

    # --- SF1: the non-matching file is excluded (proves it's a real search). ---
    assert "Alpha/Mod1/miss.feature" not in files(client, "all"), (
        "SF1: scope='all' still filters by the query — non-matching files excluded"
    )

print("PASS  SF1: scope='all' (and the omitted default) searches every .feature under the root across all projects")
