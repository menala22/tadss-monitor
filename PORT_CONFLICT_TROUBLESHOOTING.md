# TA-DSS: Port Conflict Troubleshooting Guide

> **Document Purpose:** This guide helps you resolve port conflicts when running multiple projects simultaneously. Save this for future reference!

**Created:** 2026-02-28  
**Last Updated:** 2026-02-28

---

## ⚠️ The Problem: Port Conflicts

### Your Concern

> "I have multiple projects running. What if another project also uses port 8000 for API or port 8501/8503 for dashboard? How do I avoid conflicts?"

### Why This Happens

| Port | Common Usage | Conflict Risk |
|------|-------------|---------------|
| **8000** | FastAPI default, Flask, various APIs | 🔴 HIGH |
| **8080** | HTTP alternative, Jenkins, proxies | 🔴 HIGH |
| **8501** | Streamlit default | 🟠 MEDIUM |
| **8503** | Alternative Streamlit | 🟡 LOW |
| **3000** | React, Next.js, Node.js | 🔴 HIGH |
| **5432** | PostgreSQL default | 🟠 MEDIUM |

---

## 🔍 How to Detect Port Conflicts

### Check if Port is in Use

**macOS/Linux:**
```bash
# Check if port 8000 is in use
lsof -ti:8000

# Check if port 8503 is in use
lsof -ti:8503

# See what's using the port
lsof -i :8000
```

**Windows:**
```powershell
# Check if port is in use
netstat -ano | findstr :8000
netstat -ano | findstr :8503
```

### Common Error Messages

```
ERROR:    [Errno 48] Address already in use
ERROR:    Application startup failed. Exiting.
```

```
Port 8503 is already in use
```

---

## 🛠️ Solutions

### Solution 1: Kill the Conflicting Process (Quick Fix)

**If you don't need the other project running:**

**macOS/Linux:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 8503
lsof -ti:8503 | xargs kill -9

# Kill all uvicorn processes
pkill -f "uvicorn"

# Kill all streamlit processes
pkill -f "streamlit"
```

**Windows:**
```powershell
# Find process ID
netstat -ano | findstr :8000

# Kill by PID (replace PID with actual number)
taskkill /PID <PID> /F
```

⚠️ **Warning:** This will stop the other project! Only do this if you don't need it.

---

### Solution 2: Change This Project's Ports (Recommended)

**Best for:** Running multiple projects simultaneously

#### Step 1: Choose New Ports

Pick ports that are NOT in the "Common Usage" list above. Good choices:

| Service | Safe Port Options |
|---------|------------------|
| **API** | 8010, 8020, 8030, 9000, 9001 |
| **Dashboard** | 8513, 8523, 8533, 9501, 9502 |

#### Step 2: Update Configuration Files

**For API (FastAPI):**

1. Edit `.env`:
```bash
# Change from 8000 to your chosen port
PORT=9000
```

2. Edit `src/main.py` (if hardcoded):
```python
uvicorn.run(
    "src.main:app",
    host=settings.host,
    port=9000,  # ← Change this
    reload=settings.app_env == "development",
)
```

3. Update API references in dashboard:
   - Edit `src/ui.py`
   - Find: `API_BASE_URL = "http://localhost:8000/api/v1"`
   - Change to: `API_BASE_URL = "http://localhost:9000/api/v1"`

**For Dashboard (Streamlit):**

1. Edit `.streamlit/config.toml`:
```toml
[server]
port = 9501  # ← Change from 8503
address = "localhost"
headless = true
```

2. Or use command-line flag:
```bash
streamlit run src/ui.py --server.port 9501
```

#### Step 3: Update Documentation

Update these files with your new ports:
- `README.md`
- `PROJECT_STATUS.md`
- Any deployment scripts

#### Step 4: Verify Changes

```bash
# Test new API port
curl http://localhost:9000/health

# Test new dashboard port
streamlit run src/ui.py --server.port 9501
```

---

### Solution 3: Use Environment Variables (Most Flexible)

**Best for:** Development with frequently changing projects

#### Create a `.env.local` File

```bash
# Copy existing .env
cp .env .env.local

# Add port overrides
API_PORT=9000
DASHBOARD_PORT=9501
```

#### Update Code to Use Variables

**In `src/main.py`:**
```python
from src.config import settings

# Use environment variable or default
port = int(os.getenv("API_PORT", settings.port))
```

**In `src/ui.py`:**
```python
# Get API URL from environment
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
```

#### Start with Custom Ports

```bash
# Start API on custom port
API_PORT=9000 uvicorn src.main:app --reload

# Start dashboard on custom port
streamlit run src/ui.py --server.port 9501
```

---

### Solution 4: Use Docker (Best for Production)

**Best for:** Isolation, production deployments

Each project runs in its own container with isolated ports.

**Example `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "9000:8000"  # Map host:9000 to container:8000
    environment:
      - PORT=8000  # Container always uses 8000

  dashboard:
    build: .
    ports:
      - "9501:8501"  # Map host:9501 to container:8501
    depends_on:
      - api
```

**Start with:**
```bash
docker-compose up -d
```

**Access:**
- API: http://localhost:9000
- Dashboard: http://localhost:9501

✅ **Benefit:** Container ports never conflict, only host ports matter!

---

## 📋 Quick Reference: Port Assignment Table

Keep this table handy when starting new projects:

| Project Name | API Port | Dashboard Port | Database Port | Notes |
|--------------|----------|----------------|---------------|-------|
| **TA-DSS (This)** | 8000 | 8503 | - | Default config |
| **TA-DSS (Alt 1)** | 8010 | 8513 | - | Shift by 10 |
| **TA-DSS (Alt 2)** | 9000 | 9501 | - | Clean range |
| **Project A** | 8020 | 8523 | - | Example |
| **Project B** | 8030 | 8533 | - | Example |

**Tip:** Use a spreadsheet or note-taking app to track port assignments across all your projects!

---

## 🔧 Helper Scripts

### Check All TA-DSS Ports

Create `scripts/check_ports.sh`:
```bash
#!/bin/bash

echo "Checking TA-DSS ports..."
echo ""

echo "API (8000):"
lsof -ti:8000 && echo "  ⚠️  IN USE" || echo "  ✅ Free"

echo "Dashboard (8503):"
lsof -ti:8503 && echo "  ⚠️  IN USE" || echo "  ✅ Free"

echo ""
echo "To kill processes:"
echo "  lsof -ti:8000 | xargs kill -9"
echo "  lsof -ti:8503 | xargs kill -9"
```

### Start All Services

Create `scripts/start.sh`:
```bash
#!/bin/bash

# Configuration
API_PORT=${API_PORT:-8000}
DASHBOARD_PORT=${DASHBOARD_PORT:-8503}

echo "Starting TA-DSS..."
echo "API Port: $API_PORT"
echo "Dashboard Port: $DASHBOARD_PORT"
echo ""

# Start API
echo "Starting API server..."
uvicorn src.main:app --host 0.0.0.0 --port $API_PORT &
API_PID=$!

# Wait for API to start
sleep 3

# Start Dashboard
echo "Starting dashboard..."
streamlit run src/ui.py --server.port $DASHBOARD_PORT &
DASHBOARD_PID=$!

echo ""
echo "Services started!"
echo "API PID: $API_PID"
echo "Dashboard PID: $DASHBOARD_PID"
echo ""
echo "To stop: kill $API_PID $DASHBOARD_PID"

# Wait for both processes
wait $API_PID $DASHBOARD_PID
```

**Usage:**
```bash
# Start with default ports
./scripts/start.sh

# Start with custom ports
API_PORT=9000 DASHBOARD_PORT=9501 ./scripts/start.sh
```

---

## 🚨 Common Scenarios & Solutions

### Scenario 1: "Address already in use" on API startup

**Error:**
```
ERROR:    [Errno 48] Address already in use
```

**Solution:**
```bash
# Find what's using port 8000
lsof -ti:8000

# If it's another uvicorn process
pkill -f "uvicorn"

# Or change this project's port
# Edit .env: PORT=9000
```

---

### Scenario 2: Dashboard won't start, port in use

**Error:**
```
Port 8503 is already in use
```

**Solution:**
```bash
# Find what's using port 8503
lsof -ti:8503

# If it's another streamlit process
pkill -f "streamlit"

# Or change dashboard port
# Edit .streamlit/config.toml: port = 9501
```

---

### Scenario 3: Can't access API from dashboard

**Symptom:** Dashboard shows "Unable to connect to API"

**Solution:**
1. Check API is running: `curl http://localhost:8000/health`
2. Check dashboard config matches API port
3. Update `API_BASE_URL` in `src/ui.py`

---

### Scenario 4: Multiple projects need to run simultaneously

**Solution:** Use different port ranges for each project

```
Project TA-DSS:
  API: 8000
  Dashboard: 8503

Project Alpha:
  API: 8010
  Dashboard: 8513

Project Beta:
  API: 8020
  Dashboard: 8523
```

---

## 📝 Checklist: Before Starting a New Project

Before starting any new project, run through this checklist:

- [ ] Check what ports are already in use
  ```bash
  lsof -ti:8000,8010,8020,8080,8501,8503,3000
  ```

- [ ] Assign unused ports to new project

- [ ] Document port assignments (spreadsheet/note)

- [ ] Update project configuration files

- [ ] Test that all services start successfully

- [ ] Verify services can communicate (API ↔ Dashboard)

---

## 📞 Quick Troubleshooting Commands

```bash
# Kill all Python processes (nuclear option)
pkill -9 python

# Kill all uvicorn processes
pkill -f uvicorn

# Kill all streamlit processes
pkill -f streamlit

# Check what's running
ps aux | grep -E "(uvicorn|streamlit|python)"

# Free port 8000
lsof -ti:8000 | xargs kill -9

# Free port 8503
lsof -ti:8503 | xargs kill -9

# Check if port is free
lsof -ti:8000 && echo "IN USE" || echo "FREE"
```

---

## 🎓 Key Takeaways

1. **Port conflicts are normal** when running multiple projects
2. **Always check ports** before starting a new project
3. **Document your port assignments** in a central place
4. **Use environment variables** for flexible configuration
5. **Consider Docker** for production isolation
6. **Keep a troubleshooting script** handy for quick fixes

---

## 📚 Related Documentation

- `README.md` - Project overview and quick start
- `.env.example` - Environment variable template
- `.streamlit/config.toml` - Streamlit configuration
- `PROJECT_STATUS.md` - Current project status

---

**Remember:** Port conflicts are temporary inconveniences, not blockers. With this guide, you can resolve them in minutes!

**Last Reviewed:** 2026-02-28  
**Next Review:** When starting next project
