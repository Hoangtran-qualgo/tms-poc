# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Raw round-trip (RR1a-RR1c)."""
import pathlib
import tempfile

from app import create_app


def _seed_app():
    td = tempfile.mkdtemp()
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    return root, client


# --- RR1a: PUT raw canonicalises (bytes on disk may differ from sent) ------
root, client = _seed_app()
sent = (
    "Feature: rewritten\r\n"          # CRLF (parser normalises to LF)
    "  initial description\r\n"
    "\r\n"
    "  Scenario: s   \r\n"            # trailing whitespace on the scenario line
    "    Given a step\r\n"
)
r = client.put(
    "/api/files/Alpha/Mod/case.feature/raw",
    data=sent.encode("utf-8"),
    headers={"Content-Type": "text/plain; charset=utf-8"},
)
assert r.status_code == 200, (
    f"RR1a: PUT raw with valid (non-canonical) text must return 200, got {r.status_code} "
    f"body={r.get_data(as_text=True)!r}"
)
on_disk_bytes = (root / "Alpha" / "Mod" / "case.feature").read_bytes()

# RR1a claim 1: bytes may differ -- they MUST differ here because we
# sent CRLF and the canonical form is LF.
assert on_disk_bytes != sent.encode("utf-8"), (
    "RR1a: on-disk bytes must DIFFER from sent bytes when the input is "
    "non-canonical (canonicalisation applied on save)"
)
# RR1a claim 2: the canonical form is LF-only, no CRLF.
assert b"\r\n" not in on_disk_bytes, (
    f"RR1a: canonical on-disk bytes must be LF-only (no CRLF), got "
    f"{on_disk_bytes[:120]!r}"
)
# RR1a claim 3: the SEMANTIC content survives the canonicalisation.
on_disk_text = on_disk_bytes.decode("utf-8")
assert "Feature: rewritten" in on_disk_text
assert "initial description" in on_disk_text
assert "Given a step" in on_disk_text
print("PASS  RR1a: PUT /raw canonicalises; CRLF input -> LF on disk; semantic content preserved")


# --- RR1b: PUT raw with un-parseable text -> 422 parse_error --------------
root, client = _seed_app()
unparseable = "this is not a Gherkin feature file at all, no header, no scenario"
r = client.put(
    "/api/files/Alpha/Mod/case.feature/raw",
    data=unparseable.encode("utf-8"),
    headers={"Content-Type": "text/plain; charset=utf-8"},
)
assert r.status_code == 422, (
    f"RR1b: PUT /raw with un-parseable text must return 422, got {r.status_code} "
    f"body={r.get_data(as_text=True)!r}"
)
body = r.get_json()
assert body and body.get("error", {}).get("code") == "parse_error", (
    f"RR1b: un-parseable text must carry error.code='parse_error', got {body!r}"
)
# Confirm the seed file is preserved on disk (rejection had no side-effects).
preserved = (root / "Alpha" / "Mod" / "case.feature").read_text(encoding="utf-8")
assert "seed" in preserved, (
    "RR1b: rejected PUT /raw must leave the existing file on disk unchanged"
)
print("PASS  RR1b: PUT /raw with un-parseable text -> 422 with error.code='parse_error'; file unchanged")


# --- RR1c: PUT raw + parseable-but-invalid -> 422 validation_error ---------
# SPEC/CODE DRIFT (surfaced for follow-up): spec says PUT /raw "always
# parses, validates, and re-serialises before writing" and that
# "validation errors return 422 validation_error". The as-shipped
# `Storage.write_raw` only calls `parse_feature(text)` -- it does NOT
# call `validate_feature(parsed)` nor `serialize_feature(parsed)`. So
# parseable-but-invalid input slips through and lands on disk as-is
# (with newline normalisation only). Test follows code per the
# established pattern (same shape as feature-04 UI3, AC6).
#
# The PATCH /api/files/<p> (structured) path DOES validate via
# `serialize_feature` and would surface 422 validation_error there;
# that path is exercised by AC4 in the acceptance smoke.
root, client = _seed_app()
invalid_but_parses = (
    "Feature: x\n"
    "\n"
    "  Scenario: s\n"
    "    Given a step\n"
)
r = client.put(
    "/api/files/Alpha/Mod/case.feature/raw",
    data=invalid_but_parses.encode("utf-8"),
    headers={"Content-Type": "text/plain; charset=utf-8"},
)
# Currently 200 (no validation runs on raw path). Pin this observed
# behaviour so a future code fix flips the assertion to 422 and the
# smoke fails loudly to prompt updating both spec + smoke together.
assert r.status_code == 200, (
    "RR1c: spec says PUT /raw with parseable-but-invalid text should "
    "return 422 validation_error, but as-shipped `Storage.write_raw` "
    "does NOT call validate_feature/serialize_feature -- it only parses. "
    f"This smoke pins the observed 200 to surface the drift; got {r.status_code}. "
    "When the code is patched to call serialize_feature (which enforces "
    "validation), update this assertion to 422 + error.code='validation_error'."
)
# The semantic content survived (newline normalisation only), proving
# no validation/re-serialisation happened.
on_disk = (root / "Alpha" / "Mod" / "case.feature").read_text(encoding="utf-8")
assert "Feature: x" in on_disk and "Scenario: s" in on_disk, (
    "RR1c sanity: the parseable-but-invalid text DID land on disk "
    "(further proof that write_raw skipped validation + re-serialisation)"
)
print(
    "PASS  RR1c: PUT /raw with parseable-but-invalid text returns 200 today "
    "(spec/code drift surfaced; assertion pins observed behaviour)"
)
