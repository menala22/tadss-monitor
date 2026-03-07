# Skill: git-workflow

## Purpose

Enforce consistent commit messages, branching, and deployment steps for this repo.
Fire automatically before a commit, push, or deploy, or when the user says
"commit", "push", "deploy to VM", "write a commit message", or "ship this".

---

## Commit Message Format

```
<type>: <short summary in imperative mood>

[optional body — explain WHY, not what]
[optional: files changed, issue refs]
```

### Types
| Type | Use for |
|---|---|
| `feat` | New feature or endpoint |
| `fix` | Bug fix |
| `refactor` | Code restructure, no behaviour change |
| `perf` | Performance improvement |
| `docs` | Documentation only |
| `chore` | Config, deps, tooling, scripts |
| `test` | Tests only |
| `deploy` | Deploy scripts, Dockerfile, CI changes |

### Rules
- Summary line: max 72 characters, imperative mood ("Add", not "Added" or "Adds")
- No period at end of summary
- Body optional — use it when the "why" isn't obvious from the diff
- One logical change per commit — don't bundle unrelated fixes

### Examples
```
fix: save OHLCV cache under original timeframe, not fallback

fix: strip /api/v1 before health check URL construction

feat: add Gate.io fetcher with cache save after every fetch

chore: update .env.example with new API_BASE_URL field
```

---

## Branching

- `main` — production-ready code; deploy from here
- `feature/<name>` — new features (e.g. `feature/telegram-alert-v2`)
- `fix/<name>` — isolated bug fixes (e.g. `fix/cache-key-timeframe`)
- `docs/<name>` — documentation-only changes

Merge to `main` via PR or direct push (solo dev — use judgment).

---

## Deploy to VM (Hot Copy)

Full `docker build` fails on the VM (amd64 vs arm64 mismatch in Dockerfile).
Always use the hot-copy deploy method:

```bash
# 1. Copy changed files to the running container
docker cp src/<file>.py tadss:/app/src/<file>.py

# 2. Restart the container to pick up changes
docker restart tadss

# 3. Verify the container came back up
docker ps | grep tadss
docker logs tadss --tail 30
```

For multiple files, repeat `docker cp` for each file before the restart.

Via gcloud SSH:
```bash
gcloud compute ssh tadss-vm --zone us-central1-a --command "docker cp ..."
```

### Pre-deploy checklist
- [ ] Changes committed locally
- [ ] `.env` on VM has correct API keys and `API_BASE_URL`
- [ ] If VM was restarted, check new IP and update `API_BASE_URL` in `.env`
- [ ] After deploy, check `docker logs tadss --tail 50` for startup errors

---

## Push to GitHub

```bash
git add <files>
git commit -m "<type>: <summary>"
git push origin main
```

Push after every logical unit of work — don't batch many days of commits.
