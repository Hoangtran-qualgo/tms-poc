"""S3 smoke — rename alias window: no undefined key at any observable step.

White-box check of the alias-first ordering (D4): at the moment each
referencing feature is rewritten, the vocabulary must define BOTH old_key
and new_key (the alias). Otherwise a feature would momentarily reference an
undefined key (and write_feature's cross-check would even reject new_key).

We spy on write_feature and assert the alias invariant holds on every
rewrite, then confirm the final state defines only new_key.
"""
import pathlib
import tempfile

from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    for name in ("a.feature", "b.feature"):
        s.create_file(["P", name], "desc")
        feat = s.read_feature(["P", name])
        feat.enums["components"] = "login"
        s.write_feature(["P", name], feat)

    orig_write = s.write_feature
    seen: list = []

    def _spy(parts, feature):
        vocab = s.read_project_enums("P")
        comp = vocab.get("components", {})
        assert "login" in comp and "signin" in comp, (
            f"alias window broken: {comp!r}"
        )
        seen.append(parts)
        return orig_write(parts, feature)

    s.write_feature = _spy  # type: ignore[assignment]
    n = s.rename_enum_key("P", "components", "login", "signin")
    assert n == 2, n
    assert len(seen) == 2, seen
    print("PASS  every feature rewrite saw the alias (both keys defined)")

    final = s.read_project_enums("P")
    assert final == {"components": {"signin": "Login"}}, final
    print("PASS  final vocab defines only new_key (no undefined references)")
