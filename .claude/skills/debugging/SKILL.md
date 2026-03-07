# Skill: debugging

## Purpose

Provide a systematic debug approach for issues in the scheduler, API, cache, dashboard,
and data fetchers. Fire automatically when the user reports a bug, error, or unexpected
behaviour, or enters debug mode.

---

## Triggers

- "Found a bug", "Something is broken", "Getting an error", "Not working"
- "Scheduler is skipping", "Dashboard shows 0%", "API returning 404/500"
- "Cache miss", "ETHUSD not updating", "Timeout", "Connection refused"
- "Debug mode" at session start

---

## Debug Process (always follow this order)

1. **Reproduce** — confirm the exact symptom. What is the actual vs expected behaviour?
2. **Isolate the layer** — which component owns the failure? (see Component Map below)
3. **Check logs first** — read logs before changing any code
4. **Form a hypothesis** — one specific cause, not a list of possibilities
5. **Test the hypothesis** — one targeted change or query
6. **Fix** — smallest possible change; do not refactor surrounding code
7. **Verify** — confirm the symptom is gone; check no regressions in adjacent behaviour
8. **Log the bug** — use the project-documentation skill to create a BUG-NNN entry

---

## Component Map

| Symptom | Likely layer | Where to look |
|---|---|---|
| Dashboard shows 0% PnL for a symbol | Cache miss or schema gap | `ohlcv_cache`, `routes.py`, `schemas.py` |
| Dashboard Health/Signal always NEUTRAL | Schema field missing | `PositionWithPnL` in `schemas.py` |
| API 404 on `/health` | URL construction bug | `ui.py` — `test_api_connection` |
| API timeout >10s | Blocking live fetch in route | `routes.py` — must be cache-only |
| Scheduler skipping positions | Smart scan filtering too aggressively | `monitor.py` — `_should_skip_position` |
| ETHUSD or XAGUSD never updates cache | Fetcher not calling `save_ohlcv` | `data_fetcher.py` CCXT / Gate.io paths |
| h4 cache miss for XAUUSD | Cache saved under wrong timeframe | `data_fetcher.py` — save under original key |
| VM API unreachable after VM restart | Ephemeral IP changed | Update `API_BASE_URL` in `.env` |
| `docker restart` doesn't pick up changes | File not copied before restart | Run `docker cp` first, then restart |

---

## Key Log Commands

```bash
# Live container logs (VM)
gcloud compute ssh tadss-vm --zone us-central1-a \
  --command "docker logs tadss --tail 100 -f"

# Check cache contents (VM)
gcloud compute ssh tadss-vm --zone us-central1-a \
  --command "docker exec tadss sqlite3 /app/data/tadss.db \
    'SELECT symbol, timeframe, updated_at FROM ohlcv_cache ORDER BY updated_at DESC LIMIT 20;'"

# Check open positions (VM)
gcloud compute ssh tadss-vm --zone us-central1-a \
  --command "docker exec tadss sqlite3 /app/data/tadss.db \
    'SELECT id, symbol, timeframe FROM positions WHERE status=\"open\";'"
```

---

## Common Root Causes (learned from past bugs)

- **Duplicate function definitions in `ui.py`** — Python uses the last definition, silently
  overriding earlier ones. Always grep for duplicates after editing `ui.py`.
- **Route doing live fetch** — Any external HTTP call inside a route handler blocks the
  entire event loop. Routes must be cache-only.
- **Wrong timeframe key in cache** — Twelve Data free tier falls back h4→1h. Must save
  under the *original* requested key (h4), not the fallback (1h).
- **Schema field missing from Pydantic model** — FastAPI silently drops unknown fields.
  If a dashboard column is always NEUTRAL/None, check `PositionWithPnL` in `schemas.py`.
- **`timeout` parameter shadow** — If a function is defined twice with different defaults,
  the second definition wins. Check for duplicate `fetch_*` functions in `ui.py`.

---

## Rules

- Read the relevant file before proposing a fix — never guess at line numbers
- Change one thing at a time; verify before changing the next
- Do not use `--no-verify`, `--force`, or skip safety checks to work around a symptom
- If the fix is not obvious after one hypothesis, return to step 2 and re-isolate
