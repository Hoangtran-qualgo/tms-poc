"""feature-20 / import filenames / folder-name number sequence."""

from __future__ import annotations

import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = (REPO_ROOT / "app" / "static" / "03_folder_actions.js").read_text()

match = re.search(
    r"function tmsSuggestImportFilenames\([^\n]+\) \{.*?\n\}", SOURCE, re.S
)
assert match, "F1: import filename helper is missing"

node_program = (
    match.group()
    + """
const assert = (actual, expected, label) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(label + ": " + JSON.stringify(actual));
  }
};
assert(
  tmsSuggestImportFilenames("chat", [], 3),
  ["chat_1.feature", "chat_2.feature", "chat_3.feature"],
  "F1 empty destination"
);
assert(
  tmsSuggestImportFilenames("chat", ["chat_1.feature", "CHAT_3.FEATURE"], 2),
  ["chat_2.feature", "chat_4.feature"],
  "F2 fills gaps and ignores case"
);
assert(
  tmsSuggestImportFilenames("chat", ["chat_01.feature"], 1),
  ["chat_1.feature"],
  "F3 only exact canonical leaves reserve a number"
);
"""
)
result = subprocess.run(
    ["node", "-e", node_program], text=True, capture_output=True, check=False
)
assert result.returncode == 0, f"F1–F3 helper failed: {result.stderr}"
print("PASS  F1–F3: sequential, gap-fill, case-insensitive, exact-leaf suggestions")

assert "folderNodesByPath.set(child.path, child)" in SOURCE, (
    "F4: suggestion must use the already-fetched destination folder node"
)
assert "(folder.children || []).map((child) => child.name)" in SOURCE, (
    "F4: direct child files and folders must reserve names"
)
assert 'input.dataset.generated !== "0"' in SOURCE, (
    "F4: generated fields must be distinguishable from manual fields"
)
assert "input.value === input.dataset.generatedName" in SOURCE, (
    "F4: returning to the generated value must restore automatic status"
)
assert "refreshGeneratedNames();\n    refreshGate();" in SOURCE, (
    "F4: changing project/folder must refresh generated values before gating"
)
assert "names,\n          })" in SOURCE, (
    "F4: commit must keep sending the existing names array"
)
print("PASS  F4: tree reservation, manual-edit preservation, and commit wiring")
