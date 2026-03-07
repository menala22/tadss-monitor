# Issue: Dashboard Shows No Data After VM Restart

**Date:** March 7, 2026 (Evening)  
**Status:** ✅ Resolved (temporary fix applied)

---

## Problem

After VM restart:
1. **Main page shows no positions** - blank or "Backend Connection Lost"
2. **Settings page shows old VM IP** (35.188.118.182 instead of 34.171.241.166)
3. **Scheduler shows "stopped"** - can't reach VM API

---

## Root Cause

**VM IP changed after restart:**
- Old IP: 35.188.118.182 (ephemeral, released when VM stopped)
- New IP: 34.171.241.166 (assigned when VM started)

**Dashboard was still trying to connect to old IP** because:
1. `.env` file had old IP
2. Streamlit session state cached old IP
3. Hard refresh doesn't clear Streamlit session state

---

## Solution Applied

**Restart dashboard with explicit API URL:**

```bash
pkill -9 -f streamlit
API_BASE_URL=http://34.171.241.166:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

This bypasses session state cache and forces connection to new IP.

---

## Permanent Fix (To Implement)

### Option 1: Reserve Static IP for VM (Recommended)

Prevents IP from changing on restart:

```bash
# Reserve static IP
gcloud compute addresses create tadss-static-ip --region=us-central1

# Assign to VM
gcloud compute instances delete-access-config tadss-vm \
  --access-config-name="external-nat" --zone=us-central1-a

gcloud compute instances add-access-config tadss-vm \
  --access-config-name="external-nat" \
  --address=$(gcloud compute addresses describe tadss-static-ip --region=us-central1 --format="get(address)") \
  --zone=us-central1-a
```

### Option 2: Auto-detect VM IP in Dashboard

Update `src/ui.py` to always read from `.env`:

```python
# Force refresh VM IP from .env on every load
API_BASE_URL = os.getenv("API_BASE_URL") or _load_api_url_from_env()

# Don't cache in session state, or invalidate on mismatch
if "api_base_url" not in st.session_state or st.session_state.api_base_url != API_BASE_URL:
    st.session_state.api_base_url = API_BASE_URL
```

---

## Testing Checklist

- [x] Dashboard loads without errors
- [ ] Main page shows 6 positions with data
- [ ] Settings page shows correct VM IP (34.171.241.166)
- [ ] Scheduler shows "running"
- [ ] Positions have current_price and PnL

---

## Next Steps (Tomorrow)

1. **Verify dashboard works** with current fix
2. **Reserve static IP** for VM (Option 1 above)
3. **Update dashboard code** to handle IP changes gracefully
4. **Fix cache timeout issue** documented in TROUBLESHOOTING_DASHBOARD_TIMEOUT.md

---

## Quick Reference

**Current VM IP:** 34.171.241.166  
**API URL:** http://34.171.241.166:8000/api/v1  
**Dashboard:** http://localhost:8503

**To restart dashboard:**
```bash
pkill -9 -f streamlit
API_BASE_URL=http://34.171.241.166:8000/api/v1 streamlit run src/ui.py --server.port 8503
```
