# Investigation repro (Scenario Outline import) - run individually:
#   .venv/bin/python .smoke-scratch/_investigate/outline-import/02_resolver_misses_suffixed.py
"""Blocker 1 (name mismatch): resolve_scenarios matches by EXACT (case-folded)
scenario name. The case is named with the outline's BASE name, so the report's
'<base> -- @1.<row>' rows resolve UNMATCHED -> the all-or-nothing import aborts.
The BASE name alone matches the single case (what we want after trimming).
"""
import pathlib
import tempfile

from app import create_app

BASE = "Verify retrieve agent conversations count"

with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    # The outline case carries the BASE scenario name (resolver reads only
    # feature.scenario.name; outline-ness is irrelevant to matching).
    s.create_file(["proj", "mod", "count.feature"], scenario_name=BASE)

    suffixed = [f"{BASE} -- @1.1", f"{BASE} -- @1.2"]
    res = s.resolve_scenarios("proj", suffixed)
    assert res["matched"] == {}, res
    assert res["unmatched"] == suffixed, res
    print("PASS  suffixed example-row names resolve UNMATCHED (=> import aborts):")
    print(f"        unmatched={res['unmatched']}")

    base = s.resolve_scenarios("proj", [BASE])
    assert list(base["matched"]) == [BASE], base
    print("PASS  the trimmed BASE name matches the single outline case:")
    print(f"        matched={base['matched']}")
