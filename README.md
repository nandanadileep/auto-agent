# KAIROS

Open-source autonomous background coding agent. Runs silently while you work, watches your repo, and surfaces useful nudges — TODOs you forgot, stale PRs, missing env keys — without interrupting your flow.

At midnight it consolidates everything it observed into a rolling `MEMORY.md` so it gets smarter over time.

---

## What it does

- Ticks every 5 minutes — reads your git history, modified files, TODOs/FIXMEs/HACKs
- Detects if you're at your desk (Mac idle time) and adjusts how loudly it speaks
- Sends a desktop notification when you're away, a quiet terminal line when you're present
- Never acts on code — observation and nudges only
- Nightly autodream: consolidates daily observations into persistent memory via Groq

## Quick start

```bash
git clone https://github.com/nandanadileep/Kairos-mini.git
cd Kairos-mini
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python3 main.py
```

## Configuration

Copy `.env.example` to `.env` and fill in:

| Key | Description |
|-----|-------------|
| `GITHUB_TOKEN` | Personal access token with `repo` scope |
| `GITHUB_REPO` | Repo to watch, e.g. `username/repo` |
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com) |
| `KAIROS_REPO_PATH` | Absolute path to the local repo, e.g. `/Users/you/projects/myrepo` |
| `OLLAMA_BASE_URL` | Optional, defaults to `http://localhost:11434` |

## Project structure

```
kairos/
├── daemon/
│   ├── tick.py          # main tick cycle (runs every 5 min)
│   └── scheduler.py     # APScheduler setup
├── memory/
│   ├── daily_log.py     # append observations during the day
│   ├── dream.py         # nightly consolidation into MEMORY.md
│   └── memory_md.py     # read/write MEMORY.md
├── watchers/
│   ├── github.py        # open PRs, recent commits
│   └── filesystem.py    # file change watcher (coming soon)
├── agent/
│   ├── llm.py           # Groq calls for tick and dream
│   └── tools.py         # tool stubs
├── presence.py          # Mac idle time → autonomy level
├── actions.py           # notify, print_brief, post_pr_comment
├── context.py           # builds full repo context dict
├── state.py             # SQLite action log
├── config.py            # env + constants
└── main.py              # entrypoint
```

## Models

| Role | Model |
|------|-------|
| Tick (every 5 min) | `groq/llama-3.3-70b-versatile` |
| Autodream (midnight) | `groq/llama-3.3-70b-versatile` |

## Requirements

- Python 3.10+
- Mac (presence detection uses `ioreg`)
- A Groq API key (free tier works)
