# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Search (SR1-SR4)."""
import pathlib
import tempfile

from app.storage import Storage


def _setup(s: Storage) -> None:
    """Create two projects with features containing known search bait."""
    # Alpha / mod1 / hit.feature      — description contains 'needle' twice
    # Alpha / mod1 / miss.feature     — no match
    # Alpha / mod2 / tagged.feature   — tags @needle1 @needle2 @other
    # Beta  / mod1 / other.feature    — description contains 'needle' (scope test)
    for proj in ("Alpha", "Beta"):
        s.create_folder([proj])
    for proj, mod in (("Alpha", "mod1"), ("Alpha", "mod2"), ("Beta", "mod1")):
        s.create_folder([proj, mod])

    # 'hit' description contains the needle twice (one-hit-per-file check).
    s.create_file(["Alpha", "mod1", "hit.feature"], "needle in haystack with needle again")
    s.create_file(["Alpha", "mod1", "miss.feature"], "no match here")
    s.create_file(["Alpha", "mod2", "tagged.feature"], "tagged file")
    # Inject tags on tagged.feature by re-writing the raw source.
    s.write_raw(
        ["Alpha", "mod2", "tagged.feature"],
        "Feature: tagged file\n"
        "\n"
        "  @needle1 @needle2 @other\n"
        "  Scenario: x\n"
        "    Given step\n",
    )
    s.create_file(["Beta", "mod1", "other.feature"], "needle in beta")


# --- SR1: match='text' substring on Feature.description, max one hit per file ---
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td).resolve())
    _setup(s)

    hits = s.search("needle", match="text")
    files = sorted(h["file_path"] for h in hits)
    assert files == ["Alpha/mod1/hit.feature", "Beta/mod1/other.feature"], (
        f"SR1: unexpected text hits {files}"
    )
    # 'hit.feature' description contains 'needle' twice but must yield only one hit.
    hit_count = sum(1 for h in hits if h["file_path"] == "Alpha/mod1/hit.feature")
    assert hit_count == 1, f"SR1: text mode must emit at most one hit per file, got {hit_count}"
print("PASS  SR1: search(match='text') substring-matches description, max one hit per file")


# --- SR2: match='tag' substring on Scenario.tags, multiple hits per file allowed ---
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td).resolve())
    _setup(s)

    hits = s.search("needle", match="tag")
    tagged_hits = [h for h in hits if h["file_path"] == "Alpha/mod2/tagged.feature"]
    assert len(tagged_hits) == 2, (
        f"SR2: 'tagged.feature' has 2 matching tags (needle1, needle2), got {len(tagged_hits)}"
    )
    matched_values = sorted(h["match_value"] for h in tagged_hits)
    assert matched_values == ["needle1", "needle2"], (
        f"SR2: matched tag values should be ['needle1', 'needle2'], got {matched_values}"
    )
    # Text-only matches must NOT appear in tag mode.
    text_only_files = {h["file_path"] for h in hits} - {"Alpha/mod2/tagged.feature"}
    assert text_only_files == set(), (
        f"SR2: tag mode must ignore description matches, got extras {text_only_files}"
    )
print("PASS  SR2: search(match='tag') substring-matches tags, multiple hits per file")


# --- SR3: scope filtering (all / project:<name> / module:<proj>/<mod>) ---
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td).resolve())
    _setup(s)

    all_hits = s.search("needle", match="text", scope="all")
    all_files = sorted(h["file_path"] for h in all_hits)
    assert all_files == ["Alpha/mod1/hit.feature", "Beta/mod1/other.feature"], (
        f"SR3[all]: got {all_files}"
    )

    alpha_hits = s.search("needle", match="text", scope="project:Alpha")
    alpha_files = sorted(h["file_path"] for h in alpha_hits)
    assert alpha_files == ["Alpha/mod1/hit.feature"], (
        f"SR3[project:Alpha]: got {alpha_files}"
    )

    beta_hits = s.search("needle", match="text", scope="project:Beta")
    beta_files = sorted(h["file_path"] for h in beta_hits)
    assert beta_files == ["Beta/mod1/other.feature"], (
        f"SR3[project:Beta]: got {beta_files}"
    )

    mod_hits = s.search("needle", match="text", scope="module:Alpha/mod1")
    mod_files = sorted(h["file_path"] for h in mod_hits)
    assert mod_files == ["Alpha/mod1/hit.feature"], (
        f"SR3[module:Alpha/mod1]: got {mod_files}"
    )

    # Empty module (no matches in mod2's text).
    empty_mod = s.search("needle", match="text", scope="module:Alpha/mod2")
    assert empty_mod == [], f"SR3[empty module]: expected [], got {empty_mod}"
print("PASS  SR3: scope filtering — all / project:<name> / module:<proj>/<mod>")


# --- SR4: hit shape {file_path, description, matched_field, match_value} ---
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td).resolve())
    _setup(s)

    text_hit = next(
        h for h in s.search("needle", match="text")
        if h["file_path"] == "Alpha/mod1/hit.feature"
    )
    assert set(text_hit) == {"file_path", "description", "matched_field", "match_value"}, (
        f"SR4: unexpected keys {set(text_hit)}"
    )
    assert text_hit["matched_field"] == "description", (
        f"SR4[text]: matched_field should be 'description', got {text_hit['matched_field']!r}"
    )
    assert text_hit["match_value"] == "needle", (
        f"SR4[text]: match_value should echo query, got {text_hit['match_value']!r}"
    )
    assert text_hit["description"] == "needle in haystack with needle again", (
        f"SR4[text]: description should be full, got {text_hit['description']!r}"
    )

    tag_hit = next(iter(s.search("needle", match="tag")))
    assert set(tag_hit) == {"file_path", "description", "matched_field", "match_value"}, (
        f"SR4[tag]: unexpected keys {set(tag_hit)}"
    )
    assert tag_hit["matched_field"] == "tag", (
        f"SR4[tag]: matched_field should be 'tag', got {tag_hit['matched_field']!r}"
    )
    assert tag_hit["match_value"].startswith("needle"), (
        f"SR4[tag]: match_value should be the matched tag, got {tag_hit['match_value']!r}"
    )
print("PASS  SR4: hit shape {file_path, description, matched_field, match_value}")
