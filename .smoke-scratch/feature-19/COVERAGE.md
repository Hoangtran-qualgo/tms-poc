# Feature 19 coverage — enum inline create and kind labels

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| KL1 | Kind display labels persist separately from `enums.yaml`; feature directives retain stable kind IDs. | Confirmed contract | `F19_01_inline_create_and_kind_labels.py` | covered |
| KL2 | Missing/default metadata falls back to the stable kind ID for legacy projects. | Compatibility | `F19_01_inline_create_and_kind_labels.py` | covered |
| KL3 | Removed kinds and Clear prune their display-label metadata. | Compatibility | `F19_01_inline_create_and_kind_labels.py` | covered |
| KL4 | Full label-map API validates current-kind coverage and returns saved labels. | Public surface | `F19_01_inline_create_and_kind_labels.py` | covered |
| KL5 | Manager payload/form exposes the label state and inline kind fields. | UI | `F19_01_inline_create_and_kind_labels.py` | covered |
| IC1 | Native kind/entry creation prompts are replaced by inline forms while existing ID/key validation remains. | UI | `F19_01_inline_create_and_kind_labels.py` | covered |
