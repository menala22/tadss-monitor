# Skill: coding-standards

## Purpose

Enforce consistent code style and patterns across this Python/FastAPI/Streamlit project.
Apply automatically when writing or reviewing any file under `src/`, or when the user
asks to "write", "refactor", "review", or "add" code.

---

## Language & Runtime

- Python 3.11+
- FastAPI (backend API, `src/api/`)
- Streamlit (dashboard, `src/ui.py`)
- SQLite via raw SQL or SQLAlchemy (no ORM)
- APScheduler (scheduler in `src/monitor.py`)

---

## Style Rules

### General
- Follow PEP 8. Max line length: 100 characters.
- Use type hints on all function signatures.
- No bare `except:` — always catch specific exception types.
- Prefer f-strings over `.format()` or `%` formatting.
- Constants in `UPPER_SNAKE_CASE` at module top or in `src/config.py`.

### Naming
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Pydantic schemas: `PascalCase`, suffix with schema purpose (e.g. `PositionWithPnL`)
- API route functions: verb + noun (e.g. `list_open_positions`, `get_position_by_id`)

### FastAPI (`src/api/`)
- All routes defined in `src/api/routes.py`; schemas in `src/api/schemas.py`
- Use Pydantic v2 models for request/response bodies
- Return typed responses — avoid returning raw dicts from routes
- Prefix all routes with `/api/v1/`
- Never do live external API calls inside route handlers — routes read from cache/DB only

### Data Fetchers (`src/data_fetcher.py`)
- Every fetcher (Twelve Data, CCXT, Gate.io) must call `save_ohlcv()` after a successful fetch
- Save cache under the **original requested timeframe**, not the fallback timeframe
- Log fetch source and symbol at DEBUG level; log errors at ERROR level

### Cache (`src/services/ohlcv_cache_manager.py`)
- Timeframe normalisation: h4→4h, h1→1h, d1→1d (internal → API format)
- Cache key: `(symbol, timeframe_normalised)`
- Cache reads must never block — return `None` on miss, never fetch live

### Streamlit (`src/ui.py`)
- Use `st.cache_data` with a short TTL (60–300 s) for API calls
- Set `timeout=60` on all `requests` calls to the VM API
- Avoid duplicate function definitions in the same file

### Error Handling
- Log errors with `logger.error(...)` before re-raising or returning a default
- Use `try/except` blocks only around the specific lines that can fail
- Never silently swallow exceptions that indicate data corruption or connectivity failure

---

## What Not To Do

- Do not add docstrings or comments to code you didn't change
- Do not add error handling for scenarios that can't happen
- Do not create helpers or abstractions for one-time operations
- Do not add feature flags or backward-compatibility shims
- Do not over-engineer: minimum complexity to solve the current task
