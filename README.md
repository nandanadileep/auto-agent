# auto-agent

Open-source autonomous background coding agent — inspired by Anthropic's unreleased KAIROS, built with Gemma 4 and Groq.

---

## What it does

- Watches your repo every 5 minutes and surfaces TODOs, stale PRs, missing env keys, and recent code changes
- Detects whether you're at your desk and decides how loudly to speak — desktop notification if you're away, a quiet terminal line if you're present
- Runs a nightly memory pass that consolidates everything it observed into a rolling `MEMORY.md` so context persists across sessions
- Never touches your code — observation and nudges only

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                │
│   asyncio event loop — scheduler + filesystem watcher           │
└────────┬──────────────────────────┬────────────────────────────┘
         │ every N minutes          │ file change (watchfiles)
         ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        daemon/tick.py                           │
│                                                                 │
│  1. build_context()      — git, filesystem, PRs, memory         │
│  2. get_autonomy_level() — idle time → low / medium / high      │
│  3. ask_tick_model()     — Groq LLM prompt                      │
│  4. act on response      — SLEEP / ACTION / COMMENT             │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├── context.py ──────────────────────────────────────────
         │   • git history & recently changed files
         │   • TODO / FIXME / HACK scanner (.py .js .ts .go …)
         │   • never-imported file detection (Python AST, JS grep)
         │   • dangling imports (Python AST, JS relative path check)
         │   • missing .env keys vs .env.example
         │
         ├── presence.py ─────────────────────────────────────────
         │   • macOS: ioreg HIDIdleTime
         │   • Windows: GetLastInputInfo
         │   • Linux: xprintidle
         │   → low (typing) / medium (60s) / high (threshold)
         │
         ├── watchers/github.py ──────────────────────────────────
         │   • open PRs with diff, review status, staleness
         │
         ├── state.py ────────────────────────────────────────────
         │   • SQLite via sqlite-utils
         │   • actions table — dedup, daily log, PR comments
         │   • meta table — last_tick, last_dream timestamps
         │
         └── actions.py ──────────────────────────────────────────
             • desktop notify (plyer) or terminal line (rich)
             • post PR comment via PyGithub

┌─────────────────────────────────────────────────────────────────┐
│                      memory/dream.py                            │
│   cron: midnight — reads today's log, LLM consolidates          │
│   into topic files (memory/topics/*.md) + MEMORY.md index       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    dashboard/server.py                          │
│   FastAPI — localhost:8000                                      │
│                                                                 │
│   GET  /              dark/light dashboard (single HTML page)   │
│   GET  /api/status    autonomy, actions, memory summary         │
│   GET  /api/prs       open PRs from GitHub                      │
│   GET  /api/memory    topics, today's log, dream countdown      │
│   POST /api/tick      trigger tick immediately                  │
│   POST /api/dream     trigger AutoDream in background thread    │
│   POST /api/approve/:n  post operator approval comment on PR    │
│   POST /webhook/github  GitHub webhook — HMAC verified,         │
│                          triggers tick on PR / push events      │
└─────────────────────────────────────────────────────────────────┘
```

## How it works

Every 5 minutes auto-agent wakes up, builds a snapshot of your repo (git history, modified files across 10 language extensions, TODOs, open PRs, memory topics), checks how idle your machine is to determine autonomy level, and sends that context to Groq. The model responds with `SLEEP`, `ACTION: <instruction>`, or `COMMENT: <pr>: <message>`. Actions are logged and deduplicated per day. Delivery scales with autonomy — desktop notification if you're away, a quiet terminal line if you're present, nothing if you're low autonomy and it wants to post a PR comment. At midnight AutoDream runs: the day's log gets consolidated by the LLM into per-topic memory files that persist across sessions.

## Quickstart

```bash
git clone https://github.com/nandanadileep/Kairos-mini.git
cd Kairos-mini
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python3 main.py
```

## Configuration

| Key | Required | Description |
|-----|----------|-------------|
| `GITHUB_TOKEN` | Yes | Personal access token with `repo` scope |
| `GITHUB_REPO` | Yes | Repo to watch, e.g. `username/repo` |
| `GROQ_API_KEY` | Yes | From [console.groq.com](https://console.groq.com) — free tier works |
| `GOOGLE_AI_STUDIO_KEY` | Yes | From [aistudio.google.com](https://aistudio.google.com) |
| `KAIROS_REPO_PATH` | Yes | Absolute path to the local repo, e.g. `/Users/you/projects/myrepo` |
| `OLLAMA_BASE_URL` | No | Defaults to `http://localhost:11434` |
| `GITHUB_WEBHOOK_SECRET` | No | Secret for GitHub webhook HMAC verification |
| `NGROK_AUTHTOKEN` | No | Enables real-time webhook tunnel via ngrok |
| `DEMO_MODE` | No | `true` = 1-min ticks, 10s idle threshold, verbose output |

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Scheduler | APScheduler (AsyncIO) |
| File watcher | watchfiles |
| LLM (tick) | Groq — `llama-3.3-70b-versatile` |
| LLM (dream) | Google AI Studio / Gemini |
| Local models | Ollama — `gemma4:e2b` |
| GitHub | PyGithub |
| Database | SQLite via sqlite-utils |
| Dashboard | FastAPI + uvicorn |
| Webhook tunnel | pyngrok |
| Terminal output | rich |
| Desktop notifications | plyer |

## Inspired by

Architecture inspired by the KAIROS agent described in Anthropic's Claude Code behavioral specification — a silent background daemon that observes, remembers, and nudges without interrupting flow.

## License

MIT — see [LICENSE](LICENSE)
