# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / ST3 + MS6 + TG1 + HS1 (tag mode).

ST3: match='tag' substrings against each Scenario.tags value; a file
     with multiple matching tags emits ONE hit PER matching tag.
MS6: the substring is against each tag value already stripped of '@';
     one hit per matching tag.
TG1: users type the bare value (no '@'); 'needle' matches the stored
     'needle1' / 'needle2' values, not the rendered '@needle1' chip.
HS1: tag-mode hit shape — matched_field='tag', match_value carries the
     matched tag value (without '@').

Re-owns Storage.search tag mode end-to-end through /api/search
(cross-credit: feature-02/F02_07 SR2/SR4).
"""
import pathlib
import tempfile

from app import create_app


RAW = (
    "Feature: tagged file desc\n"
    "\n"
    "  @needle1 @needle2 @other\n"
    "  Scenario: x\n"
    "    Given a step\n"
)


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    # create_file requires a non-empty description; write_raw then injects tags.
    s.create_file(["Alpha", "Mod", "tagged.feature"], "placeholder")
    s.write_raw(["Alpha", "Mod", "tagged.feature"], RAW)
    # A text-only file (description contains 'needle') to prove tag mode
    # ignores descriptions.
    s.create_file(["Alpha", "Mod", "textonly.feature"], "needle in description only")

    hits = client.get("/api/search?q=needle&match=tag").get_json()["hits"]

    # --- ST3 + MS6: one hit per matching tag (needle1, needle2). ---
    tagged = [h for h in hits if h["file_path"] == "Alpha/Mod/tagged.feature"]
    assert len(tagged) == 2, (
        f"ST3: 'tagged.feature' has 2 matching tags (needle1, needle2) → 2 hits, "
        f"got {len(tagged)}"
    )
    matched = sorted(h["match_value"] for h in tagged)
    assert matched == ["needle1", "needle2"], (
        f"MS6/HS1: matched tag values (stripped of '@') must be "
        f"['needle1','needle2'], got {matched}"
    )
    # '@other' must NOT match 'needle'.
    assert "other" not in matched, "MS6: non-matching tag '@other' must be excluded"

    # --- TG1: bare-value match, not the rendered '@'-prefixed chip. ---
    # Searching '@needle' (with the @) must NOT match the bare stored value.
    at_hits = client.get("/api/search?q=%40needle&match=tag").get_json()["hits"]
    assert at_hits == [], (
        "TG1: '@needle' (with the literal @) must NOT match — the haystack is the "
        "bare stored tag value, which has the '@' stripped"
    )

    # --- HS1: tag-mode hit shape + description still carried. ---
    h = tagged[0]
    assert set(h) == {"file_path", "description", "matched_field", "match_value"}, (
        f"HS1: tag hit keys must be the SearchHit shape, got {set(h)}"
    )
    assert h["matched_field"] == "tag", (
        f"HS1: tag-mode matched_field must be 'tag', got {h['matched_field']!r}"
    )
    assert h["description"] == "tagged file desc", (
        f"HS1: tag hit must still carry the Feature.description, got {h['description']!r}"
    )

    # --- Tag mode ignores description matches. ---
    files = {h["file_path"] for h in hits}
    assert "Alpha/Mod/textonly.feature" not in files, (
        "ST3: tag mode must ignore description text — 'textonly.feature' (needle in "
        "description, no tags) must not appear"
    )

print("PASS  ST3 + MS6 + TG1 + HS1(tag): one hit per matching tag, bare-value match (no '@'), matched_field='tag' carries the tag value")
