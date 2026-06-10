# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / AC2 -- markDirty is set-and-forget.

Spec: "Editing any field toggles the dirty indicator on; clearing the
field back to its original value leaves the indicator on (no deep
equality check -- markDirty is set-and-forget)."

Static check: every `this.markDirty(true)` call site in the tmsEditor
block is unconditional (no early-return guard that compares the
incoming value to the snapshot). We sample the wiring sites and
confirm they don't have an immediately-preceding equality-vs-snapshot
guard.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# Isolate the tmsEditor object.
m = re.search(r'const\s+tmsEditor\s*=\s*\{', JS)
assert m, "AC2: const tmsEditor must exist"
start = m.end() - 1
depth = 0
for i in range(start, len(JS)):
    c = JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            EDITOR = JS[start:i + 1]
            break


# All markDirty(true) sites.
sites = [m.start() for m in re.finditer(r'this\.markDirty\(\s*true\s*\)', EDITOR)]
assert len(sites) >= 8, (
    f"AC2: expected >= 8 markDirty(true) sites; got {len(sites)}"
)

# Each site's 200 chars of preceding context must NOT contain a
# value-vs-snapshot guard. Patterns that would be guards:
#   - if (newValue === oldValue) return
#   - if (e.target.value === <snapshot>) return
forbidden = [
    re.compile(r'===\s*this\.state\.snapshotJson'),
    re.compile(r'===\s*JSON\.parse\(\s*this\.state\.snapshotJson'),
    re.compile(r'JSON\.stringify\(\s*this\.state\.feature\s*\)\s*===\s*this\.state\.snapshotJson'),
    re.compile(r'===\s*originalValue'),
    re.compile(r'===\s*snapshotValue'),
]
for site in sites:
    ctx = EDITOR[max(0, site - 300):site]
    for pat in forbidden:
        assert not pat.search(ctx), (
            f"AC2: markDirty(true) at offset {site} is gated by a "
            f"snapshot-equality guard ({pat.pattern!r}); markDirty must "
            f"be set-and-forget per the spec"
        )

# markDirty body itself sets `this.state.dirty = !!d` unconditionally.
m_md = re.search(r'\bmarkDirty\s*\(\s*d\s*\)\s*\{', EDITOR)
assert m_md, "AC2: markDirty(d) must exist"
b_start = m_md.end() - 1
depth = 0
for i in range(b_start, len(EDITOR)):
    c = EDITOR[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            MD_BODY = EDITOR[b_start:i + 1]
            break

# No equality-with-snapshot early-return inside markDirty either.
for pat in forbidden:
    assert not pat.search(MD_BODY), (
        f"AC2: markDirty body must NOT contain snapshot-equality guard "
        f"({pat.pattern!r}); the method is set-and-forget"
    )
# First statement is the unconditional assignment.
assert re.match(
    r'\s*\{\s*this\.state\.dirty\s*=\s*!!\s*d', MD_BODY
), "AC2: markDirty's first statement must be `this.state.dirty = !!d` (unconditional)"

print("PASS  AC2: markDirty(true) sites + markDirty body are set-and-forget (no value-vs-snapshot equality guard)")
