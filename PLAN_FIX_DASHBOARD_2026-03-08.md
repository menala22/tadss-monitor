# Plan: Fix Dashboard Main Page

**Date:** March 7, 2026 (Night)  
**Status:** 📋 Plan for tomorrow

---

## Current State

### What We Know:
1. ✅ VM is running (IP: 34.171.241.166)
2. ✅ API works when tested directly: `curl http://34.171.241.166:8000/health` returns healthy
3. ✅ API returns positions: `curl http://34.171.241.166:8000/api/v1/positions/open` returns 6 positions
4. ✅ `.env` file has correct IP: `API_BASE_URL=http://34.171.241.166:8000/api/v1`
5. ❌ Dashboard shows no data / "Backend Connection Lost"
6. ❌ Test Connection button shows HTTP 404

### What We Don't Know:
1. ❓ What URL is the dashboard actually trying to connect to?
2. ❓ Is Streamlit reading the `.env` file correctly?
3. ❓ Is there a CORS issue?
4. ❓ Is the API response too slow (timeout)?
5. ❓ Is there a JavaScript error in the browser?

---

## Tomorrow's Plan (Step-by-Step)

### Step 1: Add Debug Logging to Dashboard (15 min)

**Goal:** See exactly what URL the dashboard is using.

**Add to `src/ui.py`:**
```python
# At the top of the file, after imports
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In get_current_api_url():
def get_current_api_url():
    url = st.session_state.get("api_base_url_override", API_BASE_URL)
    logger.error(f"DEBUG: get_current_api_url returning: {url}")  # Will show in terminal
    return url
```

**Then:**
1. Restart dashboard
2. Watch terminal for debug output
3. See what URL it's actually using

---

### Step 2: Check Browser Console (5 min)

**Goal:** See JavaScript errors.

**Steps:**
1. Open dashboard in browser
2. Press F12 (open DevTools)
3. Go to Console tab
4. Refresh page
5. Look for errors (red text)
6. Screenshot and share

---

### Step 3: Simple Test Page (10 min)

**Goal:** Verify if it's a Streamlit issue or API issue.

**Create `test_api.html`:**
```html
<!DOCTYPE html>
<html>
<body>
<h1>API Test</h1>
<div id="result">Loading...</div>
<script>
fetch('http://34.171.241.166:8000/api/v1/positions/open')
  .then(r => r.json())
  .then(d => document.getElementById('result').innerHTML = JSON.stringify(d, null, 2))
  .catch(e => document.getElementById('result').innerHTML = 'ERROR: ' + e)
</script>
</body>
</html>
```

**Open in browser:** `file:///path/to/test_api.html`

**If this works:** API is fine, issue is Streamlit  
**If this fails:** API/network issue

---

### Step 4: Minimal Dashboard Test (15 min)

**Goal:** Isolate the issue.

**Create `test_dashboard.py`:**
```python
import streamlit as st
import requests

st.title("Minimal Test")

API_URL = "http://34.171.241.166:8000/api/v1"
st.write(f"Testing: {API_URL}")

if st.button("Test Connection"):
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        st.write(f"Status: {resp.status_code}")
        st.write(f"Response: {resp.json()}")
    except Exception as e:
        st.write(f"ERROR: {e}")

if st.button("Get Positions"):
    try:
        resp = requests.get(f"{API_URL}/positions/open", timeout=10)
        st.write(f"Count: {len(resp.json())}")
    except Exception as e:
        st.write(f"ERROR: {e}")
```

**Run:** `streamlit run test_dashboard.py --server.port 8504`

**If this works:** Issue is in main `ui.py` code  
**If this fails:** Network/API issue

---

### Step 5: Check API Response Time (5 min)

**Goal:** Verify API isn't timing out.

**Run from local machine:**
```bash
time curl http://34.171.241.166:8000/api/v1/positions/open
```

**If <5 seconds:** API is fine  
**If >10 seconds:** API timeout issue (cache problem)

---

### Step 6: Nuclear Option - Fresh Start (30 min)

**If all else fails:**

1. **Create fresh virtual environment:**
   ```bash
   cd trading-order-monitoring-system
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create fresh `.env`:**
   ```bash
   cp .env.example .env
   # Edit with correct values
   ```

3. **Restart everything:**
   ```bash
   # VM
   docker restart tadss
   
   # Local dashboard
   streamlit run src/ui.py --server.port 8503
   ```

---

## Most Likely Issues (Ranked)

### 1. Session State Caching (40% probability)
Streamlit session state has old IP cached and won't update.

**Fix:** Clear browser storage + restart with `--server.headless=true`

### 2. API Timeout (30% probability)
API takes >30 seconds to respond (cache fetch issue), dashboard times out.

**Fix:** Revert API to simple cache (no fresh fetch), let scheduler handle updates

### 3. CORS Issue (20% probability)
Browser blocks cross-origin requests from localhost to VM.

**Fix:** Add CORS headers to FastAPI or run dashboard on VM

### 4. Code Bug (10% probability)
Something in `ui.py` is broken from recent changes.

**Fix:** Git diff to find what changed, revert suspicious changes

---

## Success Criteria

Dashboard is fixed when:
- [ ] Main page loads in <5 seconds
- [ ] Shows 6 positions with data
- [ ] Current price and PnL are populated
- [ ] Settings page shows correct VM IP (34.171.241.166)
- [ ] Test Connection button succeeds
- [ ] Scheduler shows "running"

---

## Files to Review Tomorrow

1. `src/ui.py` - Lines 71, 76-95 (API URL logic)
2. `src/ui.py` - Lines 2026-2100 (Settings page)
3. `src/api/routes.py` - Lines 112-200 (positions endpoint)
4. `.env` - Verify API_BASE_URL

---

## Commands Reference

```bash
# Check .env
grep API_BASE_URL .env

# Test API from local
curl http://34.171.241.166:8000/api/v1/positions/open

# Test API from VM
gcloud compute ssh aiagent@tadss-vm --command="curl http://localhost:8000/api/v1/positions/open"

# Restart dashboard
pkill -f streamlit; streamlit run src/ui.py --server.port 8503

# Check Streamlit logs (in terminal where it's running)
```

---

**Let's tackle this fresh tomorrow morning!** 🌙
