# Feature: DBeaver Remote Database Access
_Status: Draft_
_Last updated: 2026-03-07_

---

## What It Does

Connects DBeaver (local) to the SQLite database running inside the `tadss` Docker container on the Google Cloud VM, via SSH tunnel. Enables live SQL queries, data browsing, and CSV exports without touching production code.

**Use cases:**
- Query positions, alert_history, signal_changes tables
- Spot-check data after a monitoring run
- Export data for external analysis

---

## Key Constraint: SQLite Is File-Based

Unlike PostgreSQL or MySQL, SQLite has no server process — DBeaver accesses the raw `.db` file. For remote access, the file must be reachable from the VM's host filesystem (not just inside the container). DBeaver's SSH tunnel for SQLite works by reading the file over SFTP.

This means the critical pre-condition is: **the DB file must be on the VM host filesystem**, either via a Docker volume mount or a manual copy.

---

## Open Questions (Resolve at Session Start)

1. **Is the DB already volume-mounted to the VM host filesystem?**
   Run on VM:
   ```bash
   docker inspect tadss | grep -A 20 '"Mounts"'
   ```
   - If `Source` shows a host path (e.g. `/home/aiagent/tadss-monitor/data`) → **Scenario A** (direct access)
   - If empty or only `Type: volume` with no host path → **Scenario B** (need to expose it)

2. **What is the SSH username on the VM?**
   ```bash
   gcloud compute ssh tadss-vm --zone us-central1-a --command "whoami"
   ```

3. **Where is the gcloud SSH key?**
   Usually auto-generated at `~/.ssh/google_compute_engine` after first `gcloud compute ssh`.
   Verify: `ls -la ~/.ssh/google_compute_engine`

---

## Logic / Flow

### Scenario A — DB is already volume-mounted to VM host

```
DBeaver (local)
  └── SSH tunnel → VM :22
        └── reads /home/<user>/tadss-monitor/data/positions.db (host filesystem)
```

Steps:
1. Confirm host path from `docker inspect` output
2. Configure DBeaver connection (see Connection Setup below)
3. Test query: `SELECT * FROM positions LIMIT 5`

### Scenario B — DB is only inside the Docker container

Two options, pick one:

**Option B1 — One-time copy (snapshot, simplest)**
```bash
# On VM: copy DB from container to host filesystem
docker cp tadss:/app/data/positions.db /home/<user>/positions.db
```
Then point DBeaver at `/home/<user>/positions.db`.
- Data is a snapshot at copy time — not live
- Repeat `docker cp` when you want fresh data
- No code changes, no container restart needed

**Option B2 — Add volume mount (live data, requires restart)**
Stop the container, add `-v /home/<user>/data:/app/data` to the docker run command, restart.
- DBeaver always reads live data
- Requires a `docker stop tadss` + `docker run` with new flags
- Hot-copy any changed `.py` files back after restart

**Recommendation: Start with Option B1.** It's zero-risk and sufficient for ad-hoc queries. Upgrade to B2 if you need live reads frequently.

---

## DBeaver Connection Setup

### Step 1 — Gather values
| Setting | Value |
|---------|-------|
| SSH Host | VM IP from `.env` (`API_BASE_URL` → strip `/api/v1`) |
| SSH Port | 22 |
| SSH Username | output of `whoami` on VM |
| SSH Auth method | Public key |
| SSH Private key | `~/.ssh/google_compute_engine` |
| DB file path (remote) | host path from Scenario A, or `/home/<user>/positions.db` for B1 |

### Step 2 — Create connection in DBeaver
1. **Database** menu → **New Database Connection**
2. Select **SQLite** → Next
3. **Main tab:**
   - Path: _(leave blank for now — set after SSH is configured)_
4. **SSH tab** (click "SSH Tunnel" checkbox or tab):
   - Enable SSH tunnel: ✅
   - Host / Port: `<VM_IP>` / `22`
   - Username: `<ssh_username>`
   - Authentication: **Public Key**
   - Private key: `~/.ssh/google_compute_engine`
5. **Main tab** → Path: enter the **remote** path to `positions.db`
6. Click **Test Connection** → should show "Connected"

### Step 3 — Verify tables
```sql
-- Check all tables exist
SELECT name FROM sqlite_master WHERE type='table';

-- Spot-check positions
SELECT id, pair, timeframe, position_type, status, last_signal_status
FROM positions
WHERE status = 'open'
ORDER BY created_at DESC;

-- Recent alerts
SELECT datetime(timestamp), pair, alert_type, reason
FROM alert_history
ORDER BY timestamp DESC
LIMIT 10;

-- Recent signal changes
SELECT datetime(timestamp), pair, signal_type, previous_status, current_status
FROM signal_changes
ORDER BY timestamp DESC
LIMIT 10;
```

---

## Key Design Decisions

- **Read-only intent**: DBeaver will be used for queries and exports only. No writes to production DB via DBeaver.
- **SSH key reuse**: Use the existing gcloud SSH key (`google_compute_engine`) — no new keys needed.
- **Start with B1 snapshot**: Avoids any container restart risk. Upgrade to live mount only if needed.

---

## Out of Scope

- Writing or modifying data via DBeaver
- Migrating SQLite to PostgreSQL
- Exposing DB via HTTP (e.g. sqlite-web)
- Automating DB export/backup (separate task if needed)

---

## Pre-Session Checklist

Before starting, have these ready:

- [ ] VM is running — verify: `curl http://$(grep API_BASE_URL .env | cut -d= -f2 | sed 's|/api/v1||')/health`
- [ ] gcloud CLI authenticated: `gcloud auth list`
- [ ] DBeaver installed and open locally
- [ ] SSH key exists: `ls ~/.ssh/google_compute_engine`
- [ ] VM IP known: check `.env` → `API_BASE_URL`

---

## Session Execution Plan

| Step | Command / Action | Time |
|------|-----------------|------|
| 1 | SSH to VM, run `docker inspect tadss` → determine Scenario A or B | 5 min |
| 2A | If Scenario A: note host path → skip to Step 3 | — |
| 2B | If Scenario B: `docker cp tadss:/app/data/positions.db /home/<user>/positions.db` | 2 min |
| 3 | Configure DBeaver SSH connection (see setup above) | 10 min |
| 4 | Test connection + run verification queries | 5 min |
| 5 | Export positions to CSV as smoke test | 5 min |

**Total estimated time: 20–30 minutes**
