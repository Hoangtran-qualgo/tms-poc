# Feature 18 coverage — folder delete UI

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| FD1 | Confirmation names selected path, warns that descendant folders/test cases are permanently deleted, retains API errors, sends encoded DELETE, then refreshes parent pane and Directory tree after success. | Implemented approach; Acceptance criteria | `F18_01_folder_delete.py` | covered |
| FD2 | Delete control renders only for generic depth-2 module and depth-3..10 branch views; root, project, and typed test-run views have no control. Template values are HTML-safe data attributes. | Rules; Acceptance criteria | `F18_01_folder_delete.py` | covered |
| FD3 | Existing DELETE recursively removes selected module and descendant cases while preserving project-level enum and typed sibling data. | Goal; Acceptance criteria | `F18_01_folder_delete.py` | covered |
