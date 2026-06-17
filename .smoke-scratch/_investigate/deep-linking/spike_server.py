"""tech-10 spike (server half) — empirical, runnable now.

Questions:
  Q1. Does a non-HX GET to each /ui/<item> route return a SHELL or a bare
      FRAGMENT today? (Confirms the "core complication".)
  Q2. Does the HX-Request header change anything today? (Baseline: no.)
  Q3. If we render base.html with initial_main_url/active_tab (the proposed
      negotiation), does the shell actually point #main-pane at the item?
      (Confirms whether base.html needs parameterising.)

The CLIENT-side history behaviour (Back/Forward script rerun, const
redeclaration) is NOT testable here — see spike_htmx_notes.md.
"""
import tempfile, pathlib, re
from flask import render_template
from app import create_app
from app.storage import Storage


def has_doctype(html: str) -> bool:
    return "<!doctype" in html.lower()


def main() -> None:
    td = tempfile.mkdtemp()
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "x.feature"], scenario_name="does a thing")
    s.create_run_group("Alpha", "g1")
    s.create_run(project="Alpha", group="g1", name="Run 1",
                 file_name="run", case_paths=["Alpha/Mod/x.feature"])

    client = app.test_client()

    routes = {
        "folder": "/ui/folder/Alpha/Mod",
        "file": "/ui/file/Alpha/Mod/x.feature",
        "run": "/ui/run/Alpha/g1/run.yaml",
        "folder-test-run": "/ui/folder/Alpha/test-run/g1",
    }

    print("== Q1/Q2: shell vs fragment per route (today) ==")
    for label, url in routes.items():
        plain = client.get(url)
        hx = client.get(url, headers={"HX-Request": "true"})
        print(f"  {label:16} {url}")
        print(f"      no-header : status={plain.status_code} "
              f"doctype={has_doctype(plain.get_data(as_text=True))}")
        print(f"      HX-Request: status={hx.status_code} "
              f"doctype={has_doctype(hx.get_data(as_text=True))}")

    # The shell route for comparison.
    shell = client.get("/").get_data(as_text=True)
    print("\n== shell '/' ==")
    print(f"  doctype={has_doctype(shell)}  "
          f"main-pane hx-get -> "
          f"{re.search(r'id=\"main-pane\"[^>]*hx-get=\"([^\"]+)\"', shell).group(1)!r}")

    print("\n== Q3: render base.html WITH proposed vars (today's template) ==")
    with app.test_request_context("/ui/run/Alpha/g1/run.yaml"):
        from app.models import RUN_RESULTS
        html = render_template(
            "base.html",
            tree=s.list_tree(),
            run_results=list(RUN_RESULTS),
            initial_main_url="/ui/run/Alpha/g1/run.yaml",   # proposed kwarg
            active_tab="test-run",                          # proposed kwarg
        )
    m = re.search(r'id="main-pane"[^>]*hx-get="([^"]+)"', html)
    print(f"  base.html honours initial_main_url? main-pane hx-get -> {m.group(1)!r}")
    print("  (if this is '/ui/folder/' the template IGNORES the kwarg -> "
          "base.html must be parameterised.)")


if __name__ == "__main__":
    main()
