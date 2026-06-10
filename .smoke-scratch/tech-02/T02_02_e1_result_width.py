# Pattern: see .smoke-scratch/README.md
"""tech-02 / E1 / Result column is wide enough for the longest status.

specs/tech/02 § E1: the run-editor results table and the report case_trend
table both size their `Result` column to fit the longest defined status
(`EXECUTING`). Acceptance: no clipping/wrap for `EXECUTING` at default width.

The two tables were `w-32` (128px); E1 widens them to `w-40` (160px). This
smoke statically pins that the Result header is no longer the narrow `w-32`
and uses the agreed `w-40` in BOTH templates (kept consistent per the spec).
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
tpl = REPO / "app" / "templates"
run_html = (tpl / "run_editor.html").read_text(encoding="utf-8")
report_html = (tpl / "report_detail.html").read_text(encoding="utf-8")


def _result_header_width(html: str) -> str:
    m = re.search(r'<th class="([^"]*)">Result</th>', html)
    assert m, "Result column header not found"
    classes = m.group(1)
    widths = re.findall(r"\bw-(\d+)\b", classes)
    assert widths, f"Result header has no width class: {classes!r}"
    return f"w-{widths[0]}"


run_w = _result_header_width(run_html)
report_w = _result_header_width(report_html)

assert run_w == "w-40", f"run editor Result column must be w-40 (got {run_w})"
assert report_w == "w-40", f"report trend Result column must be w-40 (got {report_w})"
assert run_w == report_w, "run + report Result widths must stay consistent (E1)"

print(f"PASS  T02_02: Result column widened to {run_w} in run editor + report trend")
