# TMS — test case management tools

TMS is a local Next.js application for managing Gherkin `.feature` files,
test runs, and quality reports. Application data stays in
`./project/<project>/...`.

## Prerequisites

- Node.js 24.19.0 LTS

## Setup

```bash
cd js
npm ci
```

## Run locally

```bash
cd js
npm run dev
```

Open <http://127.0.0.1:3000>.

## Production build

```bash
cd js
npm run build
npm start
```

## Tests

```bash
cd js
npm test
npm run test:browser
```

## Data

Test cases live as `.feature` files under `./project/`. The hierarchy is
project → module → optional sub-folders → file.

## Docs

- `IN-PROGRESS.md` — current backlog.
- `DONE.md` — completed work / change log.
- `specs/` — feature specs, technical specs, and rules. See `specs/README.md`.
- `AGENTS.md` — contributor and agent guidelines.
