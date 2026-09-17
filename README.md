# TMS — test case management tools

Local Next.js application for editing Gherkin `.feature` files, organising
test runs, and generating quality reports. All application data is stored
under `./project/<project>/...`.

## Prerequisites

- Node.js 24.19.0 LTS

## Setup

```bash
cd js
npm ci
```

## Run

```bash
cd js
npm run dev
```

Open <http://127.0.0.1:3000>.

## Tests

```bash
cd js
npm test
npm run test:browser
```

## Data

Test cases live as `.feature` files under `./project/`. The folder hierarchy
is project → module → optional sub-folders → file.

## Docs

- `IN-PROGRESS.md` — current backlog.
- `DONE.md` — completed items / change log.
- `specs/` — feature specs, technical specs, and rules. See `specs/README.md`.
- `MIGRATION.md` and `PLAN.md` — historical migration and design evidence.
- `AGENTS.md` — engineering principles for contributors and AI agents.
