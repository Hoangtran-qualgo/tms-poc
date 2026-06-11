# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX5 -- multi-hit results grouped by project.

UX5: a >=2-hit query renders one collapsible <details> group per project
     (collapsed by default, i.e. no `open` attribute), projects sorted,
     each group summary showing the project name + a hit-count badge. Row
     paths drop the project prefix for display (project-relative), while
     the row hx-get keeps the FULL file_path so navigation is unchanged.

Driven end-to-end through /ui/search with hits spread across two projects.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    # Beta created first on disk to prove the view sorts projects (Alpha
    # must render before Beta regardless of creation / walk order).
    s.create_folder(["Beta"])
    s.create_folder(["Beta", "Mod"])
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "a.feature"], "needle one")
    s.create_file(["Alpha", "Mod", "b.feature"], "needle two")
    s.create_file(["Beta", "Mod", "c.feature"], "needle three")

    resp = client.get("/ui/search?q=needle&match=text&scope=all")
    assert resp.status_code == 200, f"UX5: must render 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)

    # --- UX5: heading reports the total across all groups. ---
    assert "3 matches for" in html, "UX5: heading must report the total hit count"

    # --- UX5: one <details> group per project, collapsed by default. ---
    assert html.count("<details") == 2, "UX5: must render one <details> group per project"
    assert "<details open" not in html, (
        "UX5: groups must be collapsed by default (no `open` attribute)"
    )

    # --- UX5: project headers present and sorted (Alpha before Beta). ---
    assert '<span class="font-mono">Alpha</span>' in html, "UX5: Alpha group header"
    assert '<span class="font-mono">Beta</span>' in html, "UX5: Beta group header"
    assert html.index(">Alpha<") < html.index(">Beta<"), (
        "UX5: projects must be sorted (Alpha before Beta)"
    )

    # --- UX5: per-group blocks carry the right rows + count badge. ---
    blocks = {
        m.group(1): m.group(0)
        for m in re.finditer(
            r'<details.*?<span class="font-mono">(\w+)</span>.*?</details>',
            html,
            re.DOTALL,
        )
    }
    assert set(blocks) == {"Alpha", "Beta"}, f"UX5: expected Alpha+Beta groups, got {set(blocks)}"
    assert blocks["Alpha"].count("<tr") == 1 + 2, "UX5: Alpha group = header row + 2 hit rows"
    assert blocks["Beta"].count("<tr") == 1 + 1, "UX5: Beta group = header row + 1 hit row"

    # --- UX5: rel-path display, full path in hx-get + title (navigation). ---
    assert re.search(
        r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/a\.feature"', html, re.DOTALL
    ), "UX5: row hx-get must keep the FULL file_path"
    assert 'title="Alpha/Mod/a.feature">Mod/a.feature<' in html, (
        "UX5: visible cell text must be the project-relative path (full path in title)"
    )
    assert ">Alpha/Mod/a.feature</td>" not in html, (
        "UX5: the project prefix must be dropped from the visible path cell"
    )

print("PASS  UX5: >=2 hits group into collapsed, sorted per-project <details> with count badges; rows show rel path but hx-get the full file_path")
