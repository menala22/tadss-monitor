# Feature: Comprehensive Security Audit
_Status: Done_
_Last updated: 2026-03-07_

## What It Does

A structured review of every attack surface in the current production setup, followed by fixing the issues found — prioritised by severity. Output is a hardened system and a documented record of what was checked, what was found, and what was changed.

---

## Areas to Audit

### 1. API Authentication — CRITICAL (known gap)
Port 8000 is open to the internet with zero authentication. Anyone who knows the VM IP can read all positions, add fake trades, or delete real ones.

**Check:**
- Can `curl http://<VM_IP>:8000/api/v1/positions/open` return data from any machine? (yes — confirmed)

**Fix:** Add API key middleware to FastAPI. Full spec in `docs/archive/TASKS_2026-03-05.md` (Task 4).

---

### 2. Firewall Rules — Medium (known gap)
GCP firewall rule `allow-tadss-api` allows port 8000 from `0.0.0.0/0` (entire internet).

**Check:**
```bash
gcloud compute firewall-rules describe allow-tadss-api
```

**Fix:** Restrict source to your home IP (`/32`). Full spec in `docs/tasks.md` (Task 5).

---

### 3. SSH Key Exposure — Medium
The gcloud SSH private key (`~/.ssh/google_compute_engine`) lives on your local machine. If your laptop is compromised, an attacker gets full VM access.

**Checks:**
```bash
# Verify key permissions are restrictive (should be 600)
ls -la ~/.ssh/google_compute_engine

# Confirm no other users have access to your Mac's SSH keys
ls -la ~/.ssh/
```

**Fixes to consider:**
- Ensure key file permissions are `600` (only you can read)
- Enable GCP OS Login (ties SSH access to your Google account — disables metadata-based keys)
- Set up key passphrase if not already set

---

### 4. Secrets and Environment Variables — Medium
`.env` on the VM contains Telegram credentials, API keys, and VM IP. Risk: accidentally committed, exposed in logs, or readable by other processes.

**Checks:**
```bash
# On VM — confirm .env is not world-readable
gcloud compute ssh tadss-vm --zone us-central1-a --command "ls -la ~/tadss-monitor/.env"

# Confirm .env is gitignored locally
grep "^\.env" .gitignore

# Confirm no secrets ever landed in git history
git log --all --full-history -- .env
git grep -i "TELEGRAM_BOT_TOKEN" $(git rev-list --all)
```

**Fix:** If secrets appear in git history, rotate the keys immediately.

---

### 5. Docker Container Security — Low-Medium
Check if the container runs as root (common default, increases blast radius if compromised).

**Checks:**
```bash
gcloud compute ssh tadss-vm --zone us-central1-a --command "docker inspect tadss --format '{{.Config.User}}'"

# Check container capabilities
gcloud compute ssh tadss-vm --zone us-central1-a --command "docker inspect tadss --format '{{.HostConfig.CapAdd}}'"
```

**Fix if running as root:** Add `USER` directive to Dockerfile and rebuild. Workaround: hot-copy approach means no rebuild needed until next full deploy.

---

### 6. sqlite-web Write Risk — Low
sqlite-web's query editor has no read-only enforcement. A mistyped `DELETE FROM positions` wipes production data.

**Check:** Is sqlite-web started with any read-only flag?
```bash
~/.local/bin/sqlite_web --help | grep -i read
```

**Fix:** Start sqlite-web with `-r` flag (read-only mode if supported), or add a note to the startup command in `docs/features/remote-db-access.md`.

---

### 7. Data at Rest — Low
SQLite DB is stored unencrypted on the VM disk. If someone gains VM access, they can read all trading data.

**Check:**
- Is the VM disk encrypted? (GCP encrypts at rest by default — verify)
```bash
gcloud compute disks describe $(gcloud compute instances describe tadss-vm --zone us-central1-a --format='get(disks[0].source)' | xargs basename) --zone us-central1-a --format='get(diskEncryptionKey)'
```

**Fix:** GCP default encryption covers this. No action needed unless using customer-managed keys.

---

### 8. Open Ports Audit — Low
Verify only expected ports are open on the VM.

**Check:**
```bash
gcloud compute firewall-rules list --filter="network=default" --format="table(name,direction,sourceRanges,allowed)"
```

Expected: port 22 (SSH) and port 8000 (API) only. Nothing else.

---

## Session Execution Plan

| Priority | Area | Action | Est. time |
|----------|------|---------|-----------|
| 1 | API authentication | Implement API key middleware (Task 4) | 30 min |
| 2 | Firewall | Restrict port 8000 to your IP (Task 5) | 10 min |
| 3 | SSH key | Check permissions, evaluate OS Login | 10 min |
| 4 | Secrets in git | Audit git history for leaked keys | 10 min |
| 5 | Docker user | Check if container runs as root | 5 min |
| 6 | sqlite-web | Test `-r` flag, update startup command | 5 min |
| 7 | Disk encryption | Verify GCP default encryption active | 5 min |
| 8 | Ports | Confirm no unexpected open ports | 5 min |

**Total estimated time: 60–90 minutes**

Start with items 1 and 2 — they address the only confirmed critical risks. Items 3–8 are verification checks that are mostly already handled by GCP defaults.

---

## Out of Scope

- HTTPS/TLS for the API (requires a domain + cert — significant effort for a personal tool)
- Database encryption at application level (SQLite encryption extensions)
- Penetration testing

---

## Audit Results — 2026-03-07

### Summary

| # | Area | Severity | Finding | Action | Status |
|---|------|----------|---------|--------|--------|
| 1 | API authentication | CRITICAL | Port 8000 open with zero auth — anyone could read/write positions | Implemented `verify_api_key` dependency on all `/api/v1/positions/*` routes. 401 without key, `/health` stays public. | ✅ Fixed |
| 2 | Firewall port 8000 | Medium | `allow-tadss-api` allows `0.0.0.0/0` | No change — lower priority now API key auth is in place. Task 5 remains in backlog. | ⚠️ Open |
| 3 | SSH private key | Medium | `~/.ssh/google_compute_engine` on laptop | Permissions verified: `600` (owner-only). `~/.ssh/` directory is `700`. No action needed. | ✅ Clean |
| 4 | Secrets in git | Medium | `.env` might have been committed | `git log -- .env` returned nothing. `git grep TELEGRAM_BOT_TOKEN` found only code references (field names/comments), no actual values. | ✅ Clean |
| 5 | Docker container user | Low-Medium | Container runs as root (`.Config.User` empty) | No extra capabilities (`CapAdd: []`). Risk accepted — fix requires Dockerfile rebuild. Deferred. | ⚠️ Accepted |
| 6 | sqlite-web write risk | Low | Query editor had no read-only enforcement | Confirmed `-r` flag is supported. Updated startup command in `docs/features/remote-db-access.md` to add `-r`. | ✅ Fixed |
| 7 | Data at rest | Low | SQLite DB stored on VM disk | `gcloud compute disks describe` returned empty `diskEncryptionKey` = GCP default encryption active. No action needed. | ✅ Clean |
| 8 | Open ports | Low | Expected: 22 + 8000 only | Found: 22 (SSH), 8000 (API), ICMP, 3389 (RDP). RDP is a GCP default firewall rule — no RDP service runs on Linux VM, nothing listening on 3389. Low risk. | ✅ Acceptable |

**Bonus finding:** VM `.env` had permissions `664` (world-readable on VM). Fixed to `600`.

---

### What Was Built / Changed

**`src/api/auth.py`** — new file
```python
def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    if not settings.api_secret_key:
        return  # Dev mode: no key configured = auth disabled
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

**`src/api/routes.py`** — router-level dependency (applies to all 9 routes at once):
```python
router = APIRouter(
    prefix="/positions",
    dependencies=[Depends(verify_api_key)],
)
```

**`src/config.py`** — new field:
```python
api_secret_key: str | None = None  # Set API_SECRET_KEY in .env to enable
```

**`src/ui.py`** — `get_api_headers()` helper + added to all 6 `requests.*` calls:
```python
def get_api_headers() -> dict:
    if API_SECRET_KEY:
        return {"X-API-Key": API_SECRET_KEY}
    return {}
```

**VM `.env`** — `API_SECRET_KEY` added (32-byte hex, generated with `openssl rand -hex 32`).

**`docs/features/remote-db-access.md`** — sqlite-web startup command updated to include `-r`.

---

### Verification

```
curl http://<VM_IP>:8000/api/v1/positions/open          → 401 Unauthorized
curl -H "X-API-Key: <key>" http://<VM_IP>:8000/...open  → 200 OK
curl http://<VM_IP>:8000/health                          → 200 OK (public)
```

---

### Remaining Risk

| Risk | Mitigation in place | To fully resolve |
|------|-------------------|-----------------|
| Port 8000 open to internet | API key auth required | Restrict firewall to your IP (Task 5) |
| Container runs as root | No extra capabilities granted | Add `USER` directive to Dockerfile on next full rebuild |
| RDP port 3389 open (GCP default rule) | No RDP service on Linux VM | Delete `default-allow-rdp` firewall rule if desired |
