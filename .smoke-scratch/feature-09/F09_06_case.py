# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / ST5 + MS2 -- case sensitivity (incl. ß quirk).

ST5: case_sensitive defaults False; case-insensitive matching is done
     via str.lower() on BOTH sides (NOT str.casefold()).
MS2: default case-insensitive via str.lower().

The str.lower()-vs-casefold() distinction is observable with German ß:
  - str.lower("Straße") == "straße"   (ß unchanged)
  - str.casefold("Straße") == "strasse"  (ß → ss)
So a 'strasse' query must NOT match a 'Straße' description under the
shipped str.lower() implementation; a 'straße' query must. This pins
the documented edge case so a future switch to casefold() fails loudly.
"""
import pathlib
import tempfile
import urllib.parse

from app import create_app


def hits(client, q, **kw):
    params = {"q": q, "match": "text", **kw}
    return client.get("/api/search?" + urllib.parse.urlencode(params)).get_json()["hits"]


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "upper.feature"], "Has NEEDLE upper")
    s.create_file(["Alpha", "Mod", "sharp.feature"], "Auf der Straße geparkt")

    # --- ST5 default: case omitted → case-insensitive. ---
    assert len(hits(client, "needle")) == 1, (
        "ST5: omitting the case param must default to case-insensitive (1 hit for "
        "'needle' vs 'NEEDLE')"
    )

    # --- MS2: case-insensitive via lower() on both sides. ---
    assert len(hits(client, "NEEDLE", case="false")) == 1, "MS2: 'NEEDLE' matches"
    assert len(hits(client, "needle", case="false")) == 1, "MS2: 'needle' matches (lowered)"
    assert len(hits(client, "NeEdLe", case="false")) == 1, "MS2: mixed case matches"

    # --- case_sensitive=True flips behaviour. ---
    assert hits(client, "needle", case="true") == [], (
        "ST5: case=true → 'needle' must NOT match 'NEEDLE'"
    )
    assert len(hits(client, "NEEDLE", case="true")) == 1, (
        "ST5: case=true → exact-case 'NEEDLE' still matches"
    )

    # --- ß quirk: str.lower(), NOT casefold(). ---
    # 'straße' (and uppercased variants that lower to it) match.
    assert len(hits(client, "straße")) == 1, (
        "MS2: 'straße' must match 'Straße' under case-insensitive lower()"
    )
    assert len(hits(client, "STRAßE")) == 1, (
        "MS2: 'STRAßE'.lower() == 'straße' must match 'Straße'"
    )
    # 'strasse' must NOT match — lower() leaves ß intact (casefold would fold it).
    assert hits(client, "strasse") == [], (
        "ST5: 'strasse' must NOT match 'Straße' — the shipped matcher uses "
        "str.lower() (ß stays ß), not str.casefold() (ß→ss). If this fails, the "
        "implementation switched to casefold()."
    )

print("PASS  ST5 + MS2: default case-insensitive via str.lower() on both sides; case=true flips; ß stays ß ('strasse' ≠ 'Straße', proving lower() not casefold())")
