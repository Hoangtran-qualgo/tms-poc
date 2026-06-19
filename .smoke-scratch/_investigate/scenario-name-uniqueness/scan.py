"""Read-only: quantify scenario-name collisions in ./project (investigate item).

Mirrors Storage.resolve_scenarios (feature-15): index Feature.scenario.name
(casefold) per project, skipping unparseable / non-UTF-8 files. Reports, per
project + overall:
  - cases (parseable .feature files with a non-empty scenario name)
  - colliding names (a name borne by >=2 cases -> would be `ambiguous` on import)
  - of those, how many are cross-folder vs same-folder
No writes.
"""
import pathlib
from collections import defaultdict

from app.storage import Storage

ROOT = pathlib.Path("project")
s = Storage(ROOT)

overall = {"cases": 0, "unparseable": 0, "colliding_names": 0,
           "cross_folder": 0, "same_folder": 0, "ambiguous_cases": 0}

for project in s.list_projects():
    index: dict[str, list[str]] = defaultdict(list)
    unparseable = 0
    try:
        paths = list(s.iter_feature_paths(project))
    except FileNotFoundError:
        paths = []
    for path in paths:
        try:
            feat = s.read_feature(path)
        except Exception:
            unparseable += 1
            continue
        name = feat.scenario.name
        if name and name.strip():
            index[name.casefold()].append(path)

    cases = sum(len(v) for v in index.values())
    collisions = {k: v for k, v in index.items() if len(v) >= 2}
    cross = same = 0
    print(f"\n=== {project} : {cases} cases, {unparseable} unparseable ===")
    for key, hits in sorted(collisions.items(), key=lambda kv: -len(kv[1])):
        parents = {p.rsplit("/", 1)[0] for p in hits}
        kind = "cross-folder" if len(parents) > 1 else "same-folder"
        if len(parents) > 1:
            cross += 1
        else:
            same += 1
        # show the real (non-casefolded) name from the first hit's file
        shown = s.read_feature(hits[0]).scenario.name
        print(f"  [{kind}] {shown!r} -> {len(hits)} cases:")
        for p in hits:
            print(f"       {p}")
    if not collisions:
        print("  (no colliding scenario names)")

    overall["cases"] += cases
    overall["unparseable"] += unparseable
    overall["colliding_names"] += len(collisions)
    overall["cross_folder"] += cross
    overall["same_folder"] += same
    overall["ambiguous_cases"] += sum(len(v) for v in collisions.values())

print("\n================ OVERALL ================")
print(f"  parseable cases ...... {overall['cases']}")
print(f"  unparseable files .... {overall['unparseable']}")
print(f"  colliding names ...... {overall['colliding_names']}")
print(f"     cross-folder ...... {overall['cross_folder']}")
print(f"     same-folder ....... {overall['same_folder']}")
print(f"  cases that would be 'ambiguous' on import ... {overall['ambiguous_cases']}")
