# feature-17 · Import test cases from multiple `.feature` files — coverage matrix

Smoke coverage against `specs/features/17-feature-multi-file-import-NEW.md`.

| Spec area | Smoke | Status |
| --- | --- | --- |
| Batch preview flattens valid files in deterministic source/scenario order with source/tag/enum context, including duplicate source labels | `F17_01_import_api` | covered |
| Preview collects source-specific invalid-type, parse, and no-scenario errors without writes | `F17_01_import_api` | covered |
| Server enforces at most 20 source files and 3 MB total UTF-8 source text | `F17_01_import_api` | covered |
| Batch commit writes all flattened cases in one destination | `F17_01_import_api` | covered |
| Cross-source duplicate scenario aborts the entire batch with zero writes | `F17_01_import_api` | covered |
| Commit revalidates batch source errors; legacy one-file request remains supported | `F17_01_import_api` | covered |
| Modal uses a multi-file picker and client-side 20-file / 3 MB-total limits | `F17_02_import_ui` | source |
| Modal sends source arrays, renders source-file context, and blocks on every preview error | `F17_02_import_ui` | source |
| One enum acknowledgement identifies every affected source and gates Import | `F17_02_import_ui` | source |

## Check result

- Feature-17: 2/2 pass.
- Feature-14 compatibility: 4/4 pass.
- Full suite: 315/321 pass. The six failures are the existing watcher
  acceptance paths under features 03, 04, 05, 06, and 10; watchdog cannot
  start fsevents in this environment.
