# Feature: Remote Database Access (sqlite-web)
_Status: Done_
_Last updated: 2026-03-07_

---

## What It Does

Provides browser-based read access to the production SQLite database on the Google Cloud VM, via SSH port forwarding. No local app install required beyond a terminal.

**Use cases:**
- Query positions, alert_history, signal_changes, ohlcv_cache tables
- Spot-check data after a monitoring run
- Export query results to CSV

---

## How to Start Each Session

**Step 1 — Open terminal and connect to VM with port forwarding:**
```bash
gcloud compute ssh tadss-vm --zone us-central1-a -- -L 8080:localhost:8080
```

**Step 2 — On the VM, start sqlite-web in read-only mode:**
```bash
~/.local/bin/sqlite_web /home/aiagent/tadss-monitor/data/positions.db --host 127.0.0.1 --port 8080 --no-browser -r
```
The `-r` flag enforces read-only mode — the query editor will reject `INSERT`, `UPDATE`, and `DELETE` statements at the DB level.
You should see: `* Running on http://127.0.0.1:8080`

**Step 3 — Open in browser:**
```
http://localhost:8080
```

Leave the terminal open — closing it stops the server.

---

## Key Details

| Detail | Value |
|--------|-------|
| DB host path on VM | `/home/aiagent/tadss-monitor/data/positions.db` |
| DB inside container | `/app/data/positions.db` |
| Volume mount | `/home/aiagent/tadss-monitor/data` → `/app/data` (confirmed) |
| SSH port forward | local 8080 → VM localhost 8080 |
| sqlite-web binary | `~/.local/bin/sqlite_web` |
| Data | Live — reads directly from the volume-mounted DB |

---

## Useful Queries

```sql
-- All open positions
SELECT id, pair, timeframe, position_type, last_signal_status,
       datetime(last_checked_at) AS last_checked
FROM positions
WHERE status = 'open'
ORDER BY created_at DESC;

-- Recent alerts
SELECT datetime(timestamp), pair, alert_type, reason
FROM alert_history
ORDER BY timestamp DESC
LIMIT 20;

-- Recent signal changes
SELECT datetime(timestamp), pair, signal_type, previous_status, current_status
FROM signal_changes
ORDER BY timestamp DESC
LIMIT 20;

-- OHLCV cache — check what's cached per symbol
SELECT symbol, timeframe, updated_at
FROM ohlcv_cache
ORDER BY updated_at DESC;
```

---

## Security

| Risk | Mitigation |
|------|------------|
| Accidental writes via query editor | sqlite-web started with `-r` (read-only) — writes rejected at DB level |
| Data stays inside SSH tunnel | All traffic encrypted — never touches the open internet |
| No new firewall ports | Port 8080 is local-only via the tunnel, not exposed on the VM |

---

## Known Limitations

- Terminal running sqlite_web must stay open during the session
- sqlite-web started with `-r` flag — write queries will be rejected at the DB level
- VM IP changes on restart → `gcloud compute ssh` still works by VM name, no action needed

---

## Installation (already done — reference only)

```bash
# On VM
sudo apt update && sudo apt install python3-pip -y
pip3 install sqlite-web
# binary lands at ~/.local/bin/sqlite_web (not in PATH by default)
```
