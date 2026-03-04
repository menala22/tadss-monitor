# TA-DSS: Session Workplan - Deep-Dive Testing & UI Improvement

**Session:** Phase 4 - Dashboard Testing & Polish  
**Date:** 2026-02-28 (Evening Session)  
**Estimated Time:** 2-3 hours  
**Status:** Ready to Start  

---

## 🎯 Session Goal

Test all dashboard features with **real data** and improve UI/UX based on findings.

---

## 📋 Session Agenda

| Time | Task | Priority | Success Criteria |
|------|------|----------|------------------|
| **0:00-0:15** | 📊 Environment Setup & Health Check | 🔴 HIGH | API + Dashboard running |
| **0:15-0:45** | 🧪 Test 1: Create Position (End-to-End) | 🔴 HIGH | Position created & visible |
| **0:45-1:15** | 🧪 Test 2: View Position Details | 🔴 HIGH | Chart + signals display |
| **1:15-1:30** | ☕ Break | - | - |
| **1:30-2:00** | 🐛 Fix Issues Discovered | 🔴 HIGH | All blockers fixed |
| **2:00-2:30** | 🎨 UI/UX Improvements | 🟠 MEDIUM | Hover effects added |
| **2:30-2:45** | 📝 Document Changes | 🟡 LOW | Session log updated |

---

## 🔧 Phase 1: Environment Setup (15 min)

### Task 1.1: Verify Services Running

```bash
# Check API server
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "...", "version": "1.0.0"}

# Check dashboard
curl http://localhost:8503/_stcore/health
# Expected: ok
```

**If API not running:**
```bash
cd "/Users/aiagent/Documents/No.3 - Qwen - Trading Order Monitoring system/trading-order-monitoring-system"
source venv/bin/activate
uvicorn src.main:app --reload &
```

**If dashboard not running:**
```bash
streamlit run src/ui.py --server.port 8503 &
```

### Task 1.2: Open Browser Tabs

| Tab | URL | Purpose |
|-----|-----|---------|
| **Dashboard** | http://localhost:8503 | Main testing |
| **API Docs** | http://localhost:8000/docs | API reference |
| **DevTools** | F12 → Console | Error monitoring |

### Task 1.3: Clear Cache

```
In dashboard sidebar:
→ Click "🔄 Refresh All Signals"
→ Clears cache for fresh data
```

---

## 🧪 Phase 2: End-to-End Testing (45 min)

### Test 2.1: Create Position via Dashboard

**Steps:**
1. Click "➕ Add New Position" in sidebar
2. Click "🟠 BTCUSD" preset button
3. Fill form:
   - Direction: LONG 🟢
   - Timeframe: 4 hours
   - Entry Price: (current BTC price from dashboard)
   - Notes: "Test position - [today's date]"
4. Click "➕ Add Position"
5. Verify success message + balloons 🎈
6. Verify redirected to Open Positions

**Expected Result:**
```
✅ Position added successfully! (ID: X)
→ Redirected to Open Positions page
→ New position appears in table
```

**If Failed:**
- [ ] Screenshot error
- [ ] Check console (F12)
- [ ] Check API logs

---

### Test 2.2: View Position in Table

**Steps:**
1. Find your test position in table
2. Verify columns display:
   - Pair: BTCUSD
   - Direction: 🟢 LONG
   - Entry: $XX,XXX.XX
   - Current: $XX,XXX.XX (should update)
   - PnL: X.XX% (color coded)
   - Timeframe: 4H
   - Status: 🟢 HEALTHY (or other)

**Expected Result:**
```
✓ All columns visible
✓ PnL color: 🟢 green if positive, 🔴 red if negative
✓ Row clickable
```

**If Failed:**
- [ ] Note which columns missing
- [ ] Check data format

---

### Test 2.3: Click Position → Detail View

**Steps:**
1. Click on your test position row
2. Verify detail view opens

**Expected Result:**
```
✅ Detail view displays:
- Large metrics (4 columns)
- Signal breakdown table
- Health status
- Candlestick chart
- Volume chart
- Close position button
- Back button
```

**If Failed:**
- [ ] Check console errors
- [ ] Verify session state working

---

### Test 2.4: Verify Signal Values Display ⚠️ CRITICAL

**Steps:**
1. In detail view, scroll to "📈 Technical Signals Breakdown"
2. Check "Signal Details" table

**Expected Result:**
```
┌────────────┬─────────────────┬──────────────────────────┬─────────────┐
│ Indicator  │     Status      │         Value            │ Conflicting │
├────────────┼─────────────────┼──────────────────────────┼─────────────┤
│ MA10       │ ✅ BULLISH      │ $62,345.67               │             │
│ MA20       │ ❌ BEARISH      │ $64,123.45               │  ⚠️ YES     │
│ MA50       │ ❌ BEARISH      │ $66,890.12               │  ⚠️ YES     │
│ MACD       │ ❌ BEARISH      │ Line: -120.45, Hist: -45│ ⚠️ YES      │
│ RSI        │ ❌ BEARISH      │ 35.2 (🔴 Bearish Zone)  │             │
└────────────┴─────────────────┴──────────────────────────┴─────────────┘
```

**Critical Checks:**
- [ ] MA10/20/50 show dollar values (not "N/A")
- [ ] MACD shows Line + Histogram values
- [ ] RSI shows number + zone
- [ ] Conflicting signals highlighted in red

**If Values Show "N/A":**
```
🐛 BUG CONFIRMED - Need to fix data flow from analyzer
File: src/ui.py
Function: render_position_detail()
Issue: Using signals.get() instead of indicator_values.get()
```

---

### Test 2.5: Verify Chart Loads ⚠️ CRITICAL

**Steps:**
1. In detail view, scroll to "📊 Price Chart with EMAs"
2. Verify chart displays

**Expected Result:**
```
✅ Candlestick chart visible
✅ EMA lines (blue, orange, purple)
✅ Entry price line (black dashed)
✅ Volume bars below
✅ Can zoom/pan
```

**Test Both:**
- [ ] Crypto pair (BTCUSD)
- [ ] Stock (AAPL) - create test position if needed

**If Chart Doesn't Load:**
- [ ] Check console errors
- [ ] Verify plotly installed
- [ ] Check data fetch for that pair

---

### Test 2.6: Test Close Position Flow

**Steps:**
1. In detail view, click "🔴 Close Position"
2. Verify confirmation dialog appears
3. Enter close price
4. Click "✅ Confirm Close"
5. Verify success message + balloons
6. Verify redirected to Open Positions
7. Verify position no longer in open list

**Expected Result:**
```
✅ Confirmation dialog appears
✅ Position closed via API
✅ Success message shown
✅ Redirected to Open Positions
✅ Position removed from open list
```

---

### Test 2.7: Test Add Position Presets

**Steps:**
1. Go to "➕ Add New Position"
2. Test each preset button:
   - [ ] 🟠 BTCUSD
   - [ ] 🔵 ETHUSD
   - [ ] 🟣 SOLUSD
   - [ ] 🍎 AAPL
   - [ ] 🚗 TSLA
3. Verify each auto-fills Pair field

**Expected Result:**
```
Each button fills Pair field with correct symbol
```

---

### Test 2.8: Test Refresh Features

**Steps:**
1. In Open Positions, click "🔄 Refresh All Signals" (sidebar)
2. Verify loading spinner
3. Verify toast: "✅ Refreshed X positions"

4. Enable "🔁 Auto-refresh every 30s"
5. Verify progress bar countdown
6. Verify page refreshes automatically

**Expected Result:**
```
✅ Manual refresh works
✅ Auto-refresh toggle works
✅ Countdown displays
✅ Positions update
```

---

### Test 2.9: Test Settings Page

**Steps:**
1. Click "⚙️ Settings" in sidebar
2. Verify each section:
   - [ ] Telegram status shows
   - [ ] Scheduler status shows
   - [ ] System info shows (version, DB path, counts)
   - [ ] Data sources show
   - [ ] Quick links work

**Expected Result:**
```
All sections display correctly
Links open in new tabs
```

---

## ☕ Break (15 min)

**Stretch! Hydrate! Rest eyes!**

---

## 🐛 Phase 3: Fix Issues Discovered (45 min)

### Based on Test Results

#### Fix 3.1: Signal Values Not Displaying
**If values show "N/A":**

**File:** `src/ui.py`  
**Function:** `render_position_detail()`  
**Fix:**
```python
# Change from:
signals = position_data.get("signals", {})

# To:
signals = position_data.get("signals", {})
indicator_values = position_data.get("indicator_values", {})

# Then use indicator_values.get() for numeric values
```

---

#### Fix 3.2: Chart Not Loading for Stocks
**If crypto works but stocks don't:**

**File:** `src/ui.py`  
**Function:** `fetch_position_with_signals()`  
**Fix:**
```python
# Verify data source detection
pair_clean = pair.replace("-", "").replace("/", "").replace("_", "")
source = "ccxt" if not (pair_clean.isalpha() and len(pair_clean) <= 5) else "yfinance"
```

---

#### Fix 3.3: Auto-Refresh Too Aggressive
**If 30s is too fast:**

**File:** `src/ui.py`  
**Function:** `render_main_page()`  
**Fix:**
```python
# Change from:
if current_time - last_refresh >= 30:

# To:
if current_time - last_refresh >= 60:  # 60 seconds
```

---

## 🎨 Phase 4: UI/UX Improvements (30 min)

### Improvement 4.1: Row Hover Effects (UX Backlog #1)

**File:** `src/ui.py`  
**Location:** Custom CSS section

**Add:**
```css
/* Table row hover effect */
div[data-testid="stDataFrame"] tr:hover {
    background-color: #f0f0f0;
    cursor: pointer;
}

/* Selected row highlight */
div[data-testid="stDataFrame"] tr.selected {
    background-color: #e3f2fd;
}
```

---

### Improvement 4.2: Add "View Details" Icon

**File:** `src/ui.py`  
**Function:** `render_positions_table()`

**Add to table data:**
```python
"Pair": f"{position.get('pair')} 👁️",
```

---

### Improvement 4.3: Improve Empty States

**File:** `src/ui.py`  
**Function:** `render_positions_table()`

**Replace empty state message with:**
```python
st.info("""
📭 No open positions yet!

**Get started:**
1. Click "➕ Add New Position" in sidebar
2. Or use quick add presets below
""")

# Add preset buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🟠 BTCUSD", use_container_width=True):
        st.session_state.preset_pair = "BTCUSD"
        st.session_state.current_page = "➕ Add New Position"
        st.rerun()
# ... etc for other presets
```

---

## 📝 Phase 5: Document Changes (15 min)

### Update Session Log

**Create:** `SESSION_LOG_2026-02-28_EVENING.md`

```markdown
# Session Log - 2026-02-28 Evening

## What We Tested
- [List all 9 tests]

## Issues Found
- [List bugs discovered]

## Fixes Applied
- [List fixes made]

## UI Improvements
- [List improvements made]

## Remaining Issues
- [List what still needs work]
```

### Update UX Backlog

**File:** `UX_BACKLOG.md`

```markdown
## Completed
- [x] Row hover effects (2026-02-28 Evening)
- [x] [Other improvements]

## Remaining
- [ ] Breadcrumb navigation
- [ ] [Other items]
```

### Update Project Status

**File:** `PROJECT_STATUS.md`

```markdown
## Phase 4: Dashboard
- Skeleton: ✅ Complete
- Testing: ✅ Complete (2026-02-28 Evening)
- Polish: 🟡 In Progress
```

---

## ✅ Success Criteria

**Session is successful if:**

- [ ] All 9 tests completed
- [ ] Signal values display correctly (or bug logged)
- [ ] Charts load for crypto AND stocks (or bug logged)
- [ ] At least 2 UI improvements implemented
- [ ] Session log updated
- [ ] Ready for next session (Phase 5 or more polish)

---

## 📞 Quick Reference

### File Locations

| File | Purpose |
|------|---------|
| `src/ui.py` | Dashboard UI (~1,600 lines) |
| `src/main.py` | FastAPI application |
| `src/api/routes.py` | API endpoints |
| `src/services/technical_analyzer.py` | Technical indicators |
| `UX_BACKLOG.md` | UX improvements backlog |
| `PROJECT_STATUS.md` | Overall project status |

### URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8503 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Common Commands

```bash
# Start API
uvicorn src.main:app --reload &

# Start Dashboard
streamlit run src/ui.py --server.port 8503 &

# Check API health
curl http://localhost:8000/health

# Kill processes
pkill -f uvicorn
pkill -f streamlit
```

---

## 🎯 Notes Section

```
[Add notes during session]

Issue discovered: 
Time: 
Fix applied: 
Result: 

UI improvement: 
Time: 
File changed: 
Result: 
```

---

**Session Start Time:** ________  
**Session End Time:** ________  
**Completed By:** ________  

**Good luck! 🚀**
