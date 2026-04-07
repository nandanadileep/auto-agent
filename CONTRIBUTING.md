# Contributing

## Local setup

```bash
git clone https://github.com/nandanadileep/Kairos-mini.git
cd Kairos-mini
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with at minimum `GITHUB_TOKEN`, `GITHUB_REPO`, `GROQ_API_KEY`, and `KAIROS_REPO_PATH`.

## Running

```bash
python3 main.py
```

KAIROS runs silently. It will print a line if it finds something actionable, or an error in red if something breaks.

## Structure

Each module has a single responsibility — keep it that way. If you're adding a new watcher, add it to `watchers/`. If you're adding a new action type, add it to `actions.py`.

## Things to work on

- `watchers/filesystem.py` — real-time file change detection with `watchfiles`
- `agent/tools.py` — structured tool definitions for the agent
- Linux/Windows presence detection (currently Mac only)
- FastAPI status endpoint using the scaffolded `fastapi`/`uvicorn` deps

## Pull requests

Keep PRs small and focused. One thing per PR. No new dependencies without a reason.
