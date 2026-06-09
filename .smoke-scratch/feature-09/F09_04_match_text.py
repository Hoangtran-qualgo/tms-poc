# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / ST2 + MS1 + MS5 + HS1 (text mode).

ST2: match='text' substrings against Feature.description; at most one
     hit per file even if the needle appears multiple times.
MS1: substring only — no regex / fuzzy (a regex metachar query matches
     literally, and only where the literal chars appear).
MS5: matches anywhere in the (real-newline) description, including text
     after a newline; the literal two-char sequence `\\n` does NOT match
     (proving search uses the parsed real-newline string, not the
     on-disk `\\n`-escaped form).
HS1: text-mode hit shape — matched_field='description', match_value
     echoes the query.

Re-owns Storage.search text mode end-to-end through /api/search
(cross-credit: feature-02/F02_07 SR1/SR4).
"""
import pathlib
import tempfile

from app import create_app


def hits(client, q, **kw):
    qs = "&".join([f"q={q}", "match=text", *(f"{k}={v}" for k, v in kw.items())])
    return client.get("/api/search?" + qs).get_json()["hits"]


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    # 'twice' description contains the needle twice → must yield ONE hit.
    s.create_file(["Alpha", "Mod", "twice.feature"], "needle and needle again")
    s.create_file(["Alpha", "Mod", "miss.feature"], "nothing relevant")
    # Multi-line description: a token lives AFTER a real newline.
    s.create_file(["Alpha", "Mod", "multiline.feature"], "first line here\nsecond WRAPTOKEN row")
    # Regex-metachar bait: literal 'a.c' present; 'abc' must not match it.
    s.create_file(["Alpha", "Mod", "regex.feature"], "literal a.c sequence")

    # --- ST2: substring match, max one hit per file. ---
    h = hits(client, "needle")
    files = sorted(x["file_path"] for x in h)
    assert files == ["Alpha/Mod/twice.feature"], (
        f"ST2: 'needle' (text) must match only twice.feature, got {files}"
    )
    assert sum(1 for x in h if x["file_path"] == "Alpha/Mod/twice.feature") == 1, (
        "ST2: a description containing the needle twice must emit exactly ONE hit"
    )

    # --- MS1: substring, not regex. ---
    # 'a.c' query matches the literal 'a.c'; 'abc' query must NOT (no regex
    # interpretation of '.').
    assert len(hits(client, "a.c")) == 1, (
        "MS1: 'a.c' must literally match 'a.c sequence'"
    )
    assert hits(client, "abc") == [], (
        "MS1: 'abc' must NOT match 'a.c' — '.' is a literal char, not a regex wildcard"
    )

    # --- MS5: matches after a real newline; literal '\\n' does NOT match. ---
    assert len(hits(client, "WRAPTOKEN")) == 1, (
        "MS5: text after a real newline in the description must be searchable "
        "(whole multi-line description is the haystack)"
    )
    # The on-disk form escapes the newline as the two chars backslash-n, but
    # search runs on the parsed real-newline string, so a literal '\\n' query
    # finds nothing.
    assert hits(client, "%5Cn") == [], (  # %5C = backslash → query is "\n" (2 chars)
        "MS5: a literal two-char '\\n' query must NOT match — the haystack is the "
        "real-newline description, not the on-disk \\n-escaped source"
    )

    # --- HS1: text-mode hit shape. ---
    hit = hits(client, "needle")[0]
    assert hit["matched_field"] == "description", (
        f"HS1: text-mode matched_field must be 'description', got {hit['matched_field']!r}"
    )
    assert hit["match_value"] == "needle", (
        f"HS1: text-mode match_value must echo the query, got {hit['match_value']!r}"
    )
    assert hit["description"] == "needle and needle again", (
        f"HS1: hit must carry the full description, got {hit['description']!r}"
    )

print("PASS  ST2 + MS1 + MS5 + HS1(text): substring (not regex), ≤1 hit/file, real-newline haystack, matched_field='description' echoes query")
