#!/usr/bin/env python3
"""Walk `.smoke-scratch/feature-*/` and run every `F<N>_*.py` smoke.

Usage:
    python .smoke-scratch/run.py
    python .smoke-scratch/run.py --filter 01           # one feature dir
    python .smoke-scratch/run.py --filter feature-02
    python .smoke-scratch/run.py --list                # enumerate, do not run
    python .smoke-scratch/run.py --verbose             # echo each PASS line

Exit code: 0 if all pass, 1 if any fail (or no smokes match the filter).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
FILE_RE = re.compile(r"^F\d+_\d+[a-z]?_.+\.py$")


def _normalize_filter(flt: str | None) -> str | None:
    if flt is None:
        return None
    return flt.removeprefix("feature-").lstrip("0") or "0"


def discover(flt: str | None) -> list[Path]:
    want = _normalize_filter(flt)
    smokes: list[Path] = []
    for feature_dir in sorted(ROOT.glob("feature-*")):
        if not feature_dir.is_dir():
            continue
        if want is not None:
            tag = feature_dir.name.removeprefix("feature-").lstrip("0") or "0"
            if tag != want:
                continue
        for path in sorted(feature_dir.iterdir()):
            if path.is_file() and FILE_RE.match(path.name):
                smokes.append(path)
    return smokes


def run_one(path: Path, verbose: bool) -> tuple[bool, str]:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    output = (proc.stdout or "") + (proc.stderr or "")
    return ok, output


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.rstrip().splitlines())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", dest="flt", metavar="<feature>",
                    help="run one feature dir (e.g. 01 or feature-01)")
    ap.add_argument("--list", action="store_true",
                    help="enumerate smokes without running them")
    ap.add_argument("--verbose", action="store_true",
                    help="echo each smoke's stdout / stderr")
    args = ap.parse_args()

    smokes = discover(args.flt)
    if not smokes:
        print(f"no smokes found (filter={args.flt!r})", file=sys.stderr)
        return 1

    if args.list:
        for p in smokes:
            print(p.relative_to(REPO_ROOT))
        return 0

    failed: list[Path] = []
    for p in smokes:
        rel = p.relative_to(REPO_ROOT)
        ok, output = run_one(p, args.verbose)
        if ok:
            print(f"PASS  {rel}")
            if args.verbose and output.strip():
                print(_indent(output))
        else:
            print(f"FAIL  {rel}")
            print(_indent(output))
            failed.append(p)

    print()
    print(f"{len(smokes) - len(failed)}/{len(smokes)} passed; "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
