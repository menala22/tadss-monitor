# CLAUDE.md — TA-DSS Trading Order Monitoring System

## Project Context

FastAPI backend + SQLite DB + OHLCV Cache, deployed on Google Cloud VM (e2-micro).
Local Streamlit dashboard connects to the VM API.
Scheduler runs every hour at :10 — fetches prices, updates cache, sends Telegram alerts.
Data sources: Twelve Data (XAUUSD, stocks, forex), Gate.io (XAGUSD), CCXT/Kraken (ETHUSD, crypto).

Deployment: hot-copy files via `docker cp src/file.py tadss:/app/src/file.py` then `docker restart tadss`
(Full docker build fails on VM — Dockerfile has `--platform linux/arm64` hardcoded.)

---

## Skills

- **project-documentation** — `.claude/skills/project-documentation/SKILL.md`
  Manages all dev docs: README, devlog, tasks, bugs, decisions, changelog, feature docs.
  Use at session start/end, after features land, bugs are found/fixed, or tech decisions are made.

- **coding-standards** — `.claude/skills/coding-standards/SKILL.md`
  Code style, naming conventions, and patterns for this Python/FastAPI/Streamlit project.
  Use when writing or reviewing any source file under `src/`.

- **git-workflow** — `.claude/skills/git-workflow/SKILL.md`
  Commit message format, branching rules, and deploy steps for this repo.
  Use before every commit or push, and when planning a deploy to the VM.

- **debugging** — `.claude/skills/debugging/SKILL.md`
  Systematic debug approach for scheduler, API, cache, and dashboard issues.
  Use whenever a bug is reported or unexpected behaviour is observed.

---

## Session Modes

Declare a mode at the start of each session:

- **build mode**  → coding-standards + project-documentation
- **doc mode**    → project-documentation only
- **debug mode**  → debugging + project-documentation (bugs workflow only)
- **plan mode**   → project-documentation (feature drafting only)
- **deploy mode** → git-workflow + project-documentation
- **review mode** → coding-standards (code review focus)
