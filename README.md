# TMS — test case management tools

A local Flask web app for editing Gherkin `.feature` files stored under
`./project/<project>/<module>/...`.

## Prerequisites

- Python 3.11+

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 -m app
```

Then open <http://127.0.0.1:5000>.

## Data

Test cases live as `.feature` files under `./project/`. The folder
hierarchy is project → module → optional sub-folders → file.

## Docs

- `PLAN.md` — architecture and design decisions.
- `IN-PROGRESS.md` — current backlog (MoSCoW).
- `DONE.md` — completed items / change log.
- `AGENTS.md` — engineering principles for contributors and AI agents.