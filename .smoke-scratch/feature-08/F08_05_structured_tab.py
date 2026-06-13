# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP4 -- structured tab scaffold.

Render-and-grep that the structured tab contains every documented
container:
  - feature description textarea (#feature-description)
  - feature tag chips region (#feature-tags-chips + #feature-tags-input)
  - background card (#background-card) with #background-steps + the
    `+ Add background step` button wired to `tmsEditor.addStep('background')`
  - scenario card: kind toggle (#kind-scenario + #kind-outline radios),
    name (#scenario-name), tag chips (#scenario-tags-chips +
    #scenario-tags-input), steps (#scenario-steps + `+ Add step`),
    examples (#examples-section + #examples-tables + `+ Add examples block`)

Cross-credit: `feature-11/F11_08_editor_scaffold.py` regression step 4 checks a
subset of these ids; this smoke covers the full set + the wiring
inline-onclicks documented in the template.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    html = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)


# Description textarea.
assert re.search(
    r'<textarea[^>]*id="feature-description"', html
), "TP4: structured tab must include <textarea id='feature-description'>"

# Feature tags region.
assert 'id="feature-tags-chips"' in html, (
    "TP4: structured tab must include #feature-tags-chips region"
)
assert re.search(
    r'<input[^>]*id="feature-tags-input"', html
), "TP4: structured tab must include <input id='feature-tags-input'>"

# Background card + steps container + add-step button.
assert 'id="background-card"' in html, (
    "TP4: structured tab must include <details id='background-card'>"
)
assert 'id="background-steps"' in html, (
    "TP4: structured tab must include #background-steps container"
)
assert re.search(
    r"onclick=\"tmsEditor\.addStep\('background'\)\"[^>]*>\s*\+\s*Add background step",
    html,
), (
    "TP4: structured tab must include a '+ Add background step' button "
    "wired to tmsEditor.addStep('background')"
)

# Scenario kind radios. Attribute order is not stable; match each <input>
# block and assert the required attributes are present.
for kind_id, kind_value in (("kind-scenario", "scenario"), ("kind-outline", "outline")):
    m_radio = re.search(
        rf'<input([^>]*\bid="{kind_id}"[^>]*)>', html
    )
    assert m_radio, f"TP4: structured tab must include <input id={kind_id!r}>"
    attrs = m_radio.group(1)
    assert 'type="radio"' in attrs, (
        f"TP4: #{kind_id} must declare type='radio'; got attrs={attrs!r}"
    )
    assert 'name="scenario-kind"' in attrs, (
        f"TP4: #{kind_id} must declare name='scenario-kind'"
    )
    assert f'value="{kind_value}"' in attrs, (
        f"TP4: #{kind_id} must declare value={kind_value!r}"
    )

# Scenario name input.
scenario_name_input = re.search(r'<input[^>]*id="scenario-name"[^>]*>', html)
assert scenario_name_input, "TP4: structured tab must include <input id='scenario-name'>"
# tech-04: scenario name is the case identity, so its placeholder reads
# "Scenario name" (NOT the stale "(optional)").
assert 'placeholder="Scenario name"' in scenario_name_input.group(0), (
    "tech-04: #scenario-name placeholder must be 'Scenario name', not '(optional)'"
)

# Scenario tags region.
assert 'id="scenario-tags-chips"' in html, (
    "TP4: structured tab must include #scenario-tags-chips region"
)
assert re.search(
    r'<input[^>]*id="scenario-tags-input"', html
), "TP4: structured tab must include <input id='scenario-tags-input'>"

# Scenario steps + add-step button.
assert 'id="scenario-steps"' in html, (
    "TP4: structured tab must include #scenario-steps container"
)
assert re.search(
    r"onclick=\"tmsEditor\.addStep\('scenario'\)\"[^>]*>\s*\+\s*Add step",
    html,
), (
    "TP4: structured tab must include a '+ Add step' button wired to "
    "tmsEditor.addStep('scenario')"
)

# Examples region + add-block button.
assert 'id="examples-section"' in html, (
    "TP4: structured tab must include #examples-section (hidden until outline)"
)
assert 'id="examples-tables"' in html, (
    "TP4: structured tab must include #examples-tables container"
)
assert re.search(
    r'onclick="tmsEditor\.addExamplesBlock\(\)"[^>]*>\s*\+\s*Add examples block',
    html,
), (
    "TP4: structured tab must include a '+ Add examples block' button "
    "wired to tmsEditor.addExamplesBlock()"
)

print(
    "PASS  TP4: structured tab scaffold renders feature description / chips / "
    "background card + add-step / scenario card with kind toggle, name, chips, "
    "steps + add-step, examples + add-block"
)
