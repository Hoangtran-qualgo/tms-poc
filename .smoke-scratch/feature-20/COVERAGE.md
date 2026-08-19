# feature-20 · Import auto-filenames — coverage matrix

| Rule | Check | Status |
| --- | --- | --- |
| Empty destination starts at `<folder>_1.feature` and increments by preview order | `F20_01` F1 | covered |
| Existing direct leaves reserve numbers case-insensitively; gaps are filled | `F20_01` F2 | covered |
| Only exact canonical leaf names reserve a number | `F20_01` F3 | covered |
| Cached tree reservation, manual-edit preservation, destination refresh, and unchanged `names` commit wire | `F20_01` F4 | covered |
