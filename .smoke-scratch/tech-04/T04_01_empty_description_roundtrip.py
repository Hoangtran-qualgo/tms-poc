# Pattern: see .smoke-scratch/README.md
"""tech-04 / testcase-detail-revamp / D1 -- empty feature description round-trips.

DO-0 de-risk (spec U1): once the description-non-empty model rule is
removed, a Feature whose `description` is empty must:
  1. validate cleanly (no ValidationError);
  2. serialize to a bare `Feature:` header line;
  3. parse back with description == "" and the scenario name preserved;
  4. re-serialize byte-identically (canonical idempotence);
  5. be creatable + readable through Storage.create_file with an empty
     description (the create path no longer rejects it).
"""
import pathlib
import tempfile

from app import create_app
from app.gherkin_io import parse_feature, serialize_feature
from app.models import Feature, Scenario, Step, validate_feature


# --- 1-4: pure model round-trip ------------------------------------------
feat = Feature(
    description="",
    scenario=Scenario(
        kind="scenario",
        name="Pay with credit card",
        steps=[Step(keyword="Given", text="a logged-in user")],
    ),
)

# 1. validates cleanly now that the description rule is gone.
validate_feature(feat)
print("PASS  D1: empty-description Feature validates (model rule removed)")

# 2. serializes to a bare `Feature:` header.
text = serialize_feature(feat)
header = next(ln for ln in text.splitlines() if ln.startswith("Feature:"))
assert header.strip() == "Feature:", f"expected bare 'Feature:' header, got {header!r}"
print("PASS  D1: empty description serializes to a bare 'Feature:' line")

# 3. parses back with empty description + preserved scenario name.
back = parse_feature(text)
assert back.description == "", f"description must round-trip empty, got {back.description!r}"
assert back.scenario.name == "Pay with credit card", (
    f"scenario name must survive the round-trip, got {back.scenario.name!r}"
)
print("PASS  D1: empty description + scenario name round-trip through parse")

# 4. canonical idempotence.
assert serialize_feature(back) == text, "re-serialize must be byte-identical"
print("PASS  D1: empty-description serialize is idempotent")


# --- 5: storage create path accepts an empty description -----------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])

    # Previously raised ValidationError; must now succeed.
    s.create_file(["Alpha", "Mod", "empty.feature"], "")
    read = s.read_feature("Alpha/Mod/empty.feature")
    assert read.description == "", (
        f"create_file with empty description must persist '', got {read.description!r}"
    )
    print("PASS  D1: Storage.create_file accepts an empty description")
