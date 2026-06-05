# TMS — test case management tools

A local Flask web app for editing Gherkin `.feature` files stored under
`./project/<project>/<module>/...`.

## Prerequisites

- Python 3.11+

## Setup

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (cmd.exe):**

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Run

With the virtual environment activated (see above), the same command
works on every platform:

```bash
python -m app
```

If you prefer not to activate the venv, call the interpreter directly:

- macOS / Linux: `.venv/bin/python -m app`
- Windows: `.venv\Scripts\python.exe -m app`

Then open <http://127.0.0.1:5000>.

## Data

Test cases live as `.feature` files under `./project/`. The folder
hierarchy is project → module → optional sub-folders → file.

## Docs

- `PLAN.md` — architecture and design decisions.
- `IN-PROGRESS.md` — current backlog (MoSCoW).
- `DONE.md` — completed items / change log.
- `specs/` — per-feature specifications (`specs/features/`) and
  cross-cutting tech / business rules (`specs/rules/`). See
  `specs/README.md`.
- `AGENTS.md` — engineering principles for contributors and AI agents.