# auto-agent

Open-source autonomous background coding agent — inspired by Anthropic's unreleased KAIROS, built with Gemma 4 and Groq.

---

## What it does

- Watches your repo every 5 minutes and surfaces TODOs, stale PRs, missing env keys, and recent code changes
- Detects whether you're at your desk and decides how loudly to speak — desktop notification if you're away, a quiet terminal line if you're present
- Runs a nightly memory pass that consolidates everything it observed into a rolling `MEMORY.md` so context persists across sessions
- Never touches your code — observation and nudges only

## How it works

Every 5 minutes auto-agent wakes up, builds a snapshot of your repo (git history, modified files, TODOs, open PRs, memory), checks how idle your machine is to determine autonomy level, and sends that context to Groq. The model responds with either `SLEEP` (nothing useful to say) or `ACTION: <instruction>`. If it's an action, auto-agent logs it, deduplicates it against today's history, and delivers it — as a desktop notification if you're away, or a single dim line in your terminal if you're present. At midnight it runs an autodream: the day's observations get merged into `MEMORY.md` by the LLM, keeping the file under 200 lines.

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
| `AGENT_REPO_PATH` | Yes | Absolute path to the local repo, e.g. `/Users/you/projects/myrepo` |
| `OLLAMA_BASE_URL` | No | Defaults to `http://localhost:11434` |

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Scheduler | APScheduler (AsyncIO) |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Local models | Ollama — `gemma4:e2b` |
| GitHub | PyGithub |
| Terminal output | rich |
| Desktop notifications | plyer |

## Inspired by

Architecture inspired by the KAIROS agent described in Anthropic's Claude Code behavioral specification — a silent background daemon that observes, remembers, and nudges without interrupting flow.

## License

MIT — see [LICENSE](LICENSE)
