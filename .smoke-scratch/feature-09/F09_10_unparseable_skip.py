# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / MS4 -- unparseable files are silently skipped.

MS4: files that fail to parse (GherkinParseError / OSError /
     UnicodeDecodeError) are silently skipped during the walk. A
     malformed .feature whose raw bytes contain the needle must NOT
     appear in results; a sibling parseable file with the same needle
     must still match.

Re-owns the storage walk's try/except skip end-to-end through
/api/search. Writes the broken file directly to disk (bypassing
Storage.write_raw, which would reject malformed Gherkin) so the walk
encounters a real on-disk parse failure.
"""
import pathlib
import tempfile

from app import create_app


def files(client, q="needle"):
    h = client.get(f"/api/search?q={q}&match=text&scope=all").get_json()["hits"]
    return sorted(x["file_path"] for x in h)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    # A parseable file that genuinely matches.
    s.create_file(["Alpha", "Mod", "good.feature"], "needle lives here")

    # A malformed .feature written straight to disk: its raw text contains
    # the needle, but it is NOT valid Gherkin, so read_feature() raises and
    # the walk must skip it.
    broken = root / "Alpha" / "Mod" / "broken.feature"
    broken.write_text(
        "this is not gherkin at all :: needle needle\n   ??? %%% \n",
        encoding="utf-8",
    )
    assert broken.exists(), "precondition: broken file written to disk"

    # --- MS4: only the parseable file is returned. ---
    result = files(client)
    assert result == ["Alpha/Mod/good.feature"], (
        f"MS4: malformed broken.feature must be silently skipped, got {result}"
    )

    # --- MS4: the search still succeeds (no 500) despite the bad file. ---
    resp = client.get("/api/search?q=needle&match=text&scope=all")
    assert resp.status_code == 200, (
        f"MS4: an unparseable file in the walk must not crash search, got {resp.status_code}"
    )

print("PASS  MS4: unparseable .feature files are silently skipped during the search walk (no crash, no spurious hit)")
