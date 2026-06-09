# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / SF3 -- scope='module:<proj>/<mod>'.

SF3: scope='module:<proj>/<mod>' restricts to files whose FIRST TWO
     path segments match <proj> and <mod>.

Re-owns the module-scope branch end-to-end through /api/search
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

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod1"])
    s.create_folder(["Alpha", "Mod2"])
    # A nested sub-folder under Mod1 to prove the filter is a prefix on the
    # first two segments (deeper files under the module still count).
    s.create_folder(["Alpha", "Mod1", "Sub"])
    s.create_file(["Alpha", "Mod1", "a.feature"], "needle one")
    s.create_file(["Alpha", "Mod1", "Sub", "deep.feature"], "needle deep")
    s.create_file(["Alpha", "Mod2", "b.feature"], "needle two")

    # --- SF3: module:Alpha/Mod1 → Mod1 files (incl. nested), NOT Mod2. ---
    assert files(client, "module:Alpha/Mod1") == [
        "Alpha/Mod1/Sub/deep.feature",
        "Alpha/Mod1/a.feature",
    ], (
        f"SF3: module:Alpha/Mod1 must return Mod1's files (including nested "
        f"sub-folders), got {files(client, 'module:Alpha/Mod1')}"
    )

    # --- SF3: module:Alpha/Mod2 → only Mod2. ---
    assert files(client, "module:Alpha/Mod2") == ["Alpha/Mod2/b.feature"], (
        f"SF3: module:Alpha/Mod2 must return only Mod2's file, got {files(client, 'module:Alpha/Mod2')}"
    )

    # --- SF3: a non-existent module → no hits (not an error). ---
    assert files(client, "module:Alpha/Ghost") == [], (
        "SF3: module:<proj>/<unknown> must return [] (missing base dir → empty)"
    )

print("PASS  SF3: scope='module:<proj>/<mod>' restricts to the first-two-segment match (including nested sub-folders)")
