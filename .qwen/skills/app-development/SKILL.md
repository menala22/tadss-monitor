# App Development Skill

**Skill Name:** `app-development`
**Version:** 1.0
**Created:** March 5, 2026
**Expertise Level:** Expert

---

## Overview

Specialized AI agent for full-stack application development with focus on **Python/FastAPI backends**, **Streamlit dashboards**, **cloud deployment**, and **production-ready systems**.

---

## Core Capabilities

### 1. Project Setup & Scaffolding

**What I Do:**
- Create project structure (src/, tests/, scripts/, docs/)
- Set up virtual environments (pyenv, venv)
- Configure dependencies (requirements.txt, pip-tools)
- Create .gitignore, .env.example templates
- Set up pre-commit hooks, linting (black, flake8)

**Project Structure I Use:**
```
project-name/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings management
│   ├── database.py          # DB connections
│   ├── models/              # SQLAlchemy models
│   ├── api/                 # API routes & schemas
│   ├── services/            # Business logic
│   └── utils/               # Helper functions
├── tests/
│   ├── test_*.py
│   └── conftest.py
├── scripts/
│   ├── deploy-*.sh
│   └── *.py
├── docs/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

### 2. Backend Development (FastAPI)

**What I Build:**
- RESTful APIs with automatic OpenAPI docs
- Async/await endpoints for performance
- Pydantic models for validation
- Dependency injection for database sessions
- Error handling with proper HTTP status codes
- CORS configuration for frontend access

**Standard Patterns:**
```python
# FastAPI app structure
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

app = FastAPI(title="My API", version="1.0")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoint
@app.get("/api/v1/resource")
def get_resource(id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Not found")
    return resource
```

---

### 3. Frontend Development (Streamlit)

**What I Build:**
- Interactive dashboards
- Real-time data visualization
- Form inputs for data entry
- Session state management
- Responsive layouts

**Standard Patterns:**
```python
# Streamlit dashboard structure
import streamlit as st

st.set_page_config(page_title="Dashboard", layout="wide")

# Sidebar for navigation
page = st.sidebar.selectbox("Page", ["Overview", "Details", "Settings"])

# Main content
if page == "Overview":
    st.title("Overview")
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", value=100, delta=10)
    
    # Charts
    st.line_chart(data)
    
    # Tables
    st.dataframe(df)
```

---

### 4. Database Management

**What I Handle:**
- SQLAlchemy ORM setup
- Database migrations (Alembic)
- Connection pooling
- SQLite (MVP) → PostgreSQL (production) migrations
- Database backup scripts
- Query optimization

**Standard Patterns:**
```python
# Database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model example
class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    pair = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
```

---

### 5. Cloud Deployment

**Platforms I Deploy To:**

| Platform | Use Case | Cost |
|----------|----------|------|
| **Google Cloud e2-micro** | 24/7 VM, full control | $0 (free tier) |
| **Railway** | Easy PaaS deployment | ~$0.21/month |
| **GitHub Actions** | Scheduled jobs, CI/CD | FREE (2K min/month) |
| **Hugging Face Spaces** | Docker apps, demos | FREE |
| **Oracle Cloud Free** | Larger VMs (4 OCPU, 24GB) | $0 |

**Deployment Workflow:**
```bash
# 1. Pre-deployment checks
./scripts/pre-deploy-check.sh

# 2. Deploy to production
./scripts/deploy-to-production.sh

# 3. Verify deployment
./scripts/post-deploy-check.sh

# 4. Rollback if needed
./scripts/rollback.sh
```

**Docker Configuration:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 6. Testing & Quality Assurance

**What I Implement:**
- Unit tests (pytest)
- Integration tests
- End-to-end tests
- Code coverage reports
- Pre-commit hooks
- CI/CD pipelines

**Test Structure:**
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_position():
    response = client.post("/api/v1/positions/open", json={
        "pair": "BTCUSD",
        "entry_price": 50000,
        "position_type": "LONG",
        "timeframe": "h4"
    })
    assert response.status_code == 201
    assert "id" in response.json()
```

---

### 7. Environment & Configuration

**Environment Management:**
```bash
# .env.example (COMMITTED to git)
TELEGRAM_BOT_TOKEN=your_token_here
DATABASE_URL=sqlite:///./data/app.db
APP_ENV=development
LOG_LEVEL=INFO

# .env (NEVER commit)
TELEGRAM_BOT_TOKEN=actual_token
```

**Configuration Class:**
```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.db"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

---

### 7.5 Development Workflow & Best Practices

**Local vs Production Code Management:**

**Environment Separation:**
```bash
# Local Development (.env.local - NEVER commit)
TELEGRAM_BOT_TOKEN=test_bot_token
DATABASE_URL=sqlite:///./data/positions-local.db
PORT=8001
APP_ENV=development

# Production (.env on VM - NEVER commit)
TELEGRAM_BOT_TOKEN=production_bot_token
DATABASE_URL=sqlite:///./data/positions.db
PORT=8000
APP_ENV=production
```

**Git Branch Strategy:**
```
main (production) ← Always deployable
  ↑
  └── feature/your-feature (local development)
```

**Daily Workflow:**
```bash
# 1. Start fresh
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. Develop locally (port 8001)
uvicorn src.main:app --reload --port 8001

# 3. Test locally
pytest tests/ -v
curl http://localhost:8001/health

# 4. Commit (don't deploy yet)
git add .
git commit -m "feat: my feature"
git push origin feature/my-feature

# 5. When ready, merge and deploy
git checkout main
git merge feature/my-feature
git push origin main
./scripts/deploy-to-production.sh
```

**Pre-Deployment Checklist:**
```bash
# Run before EVERY deployment
./scripts/pre-deploy-check.sh
# Checks:
# - No uncommitted changes
# - On main branch
# - Tests pass
# - .env not in git
```

**Deployment Automation:**
```bash
# Automated deployment script
./scripts/deploy-to-production.sh
# Does:
# - Pre-deployment checks
# - Git pull on VM
# - Database backup
# - Docker rebuild
# - Container restart
# - Health check
# - Post-deployment verification
```

**Database Management:**
```bash
# Backup before changes
./scripts/backup-database.sh

# Run migrations
python src/migrations/migration_YYYYMMDD_feature.py

# Rollback if needed
./scripts/rollback.sh
```

**Prevent Discrepancies - Golden Rules:**
- ✅ Never develop on `main` branch
- ✅ Never commit `.env` files
- ✅ Never deploy untested code
- ✅ Always backup before deployment
- ✅ Always health check after deployment
- ✅ Use separate environments (local ≠ production)
- ✅ Tag production deployments
- ✅ Document everything

---

### 8. Monitoring & Logging

**What I Set Up:**
- Structured logging (JSON format)
- Log rotation
- Error tracking
- Health check endpoints
- Performance monitoring
- Alert notifications (Telegram, email)

**Logging Setup:**
```python
import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

---

### 9. Security Best Practices

**What I Implement:**
- Environment variables for secrets (never hardcode)
- Input validation (Pydantic)
- SQL injection protection (SQLAlchemy ORM)
- CORS configuration
- Rate limiting
- Authentication/Authorization (JWT, OAuth2)
- HTTPS enforcement

**Security Checklist:**
- [ ] `.env` files in `.gitignore`
- [ ] API keys in environment variables
- [ ] Database credentials secured
- [ ] CORS properly configured
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting on public endpoints
- [ ] HTTPS in production

---

### 10. Documentation

**What I Create:**
- README.md with quick start
- API documentation (OpenAPI/Swagger)
- Deployment guides
- Troubleshooting guides
- Architecture diagrams
- Code comments (sparingly, focus on why not what)

**README Structure:**
```markdown
# Project Name

> Brief description

**Status:** 🟢 Production Ready
**Python:** 3.12
**Tests:** XX passing

## Quick Start

1. Clone & setup
2. Install dependencies
3. Configure environment
4. Run tests
5. Start server

## Features

- Feature 1
- Feature 2

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /api/v1/resource | Create resource |

## Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
```

---

## When to Use This Skill

### ✅ Appropriate Use Cases

1. **New Application Development**
   - "Build a FastAPI backend with Streamlit dashboard"
   - "Create a trading monitoring system"
   - "Set up automated alerts via Telegram"

2. **Deployment & DevOps**
   - "Deploy to Google Cloud free tier"
   - "Set up CI/CD with GitHub Actions"
   - "Create Docker configuration"

3. **Development Workflow**
   - "How to manage local vs production code?"
   - "What's the best git branch strategy?"
   - "How to set up automated deployments?"
   - "How to prevent local/prod discrepancies?"

4. **Code Review & Optimization**
   - "Review my FastAPI endpoints"
   - "Optimize database queries"
   - "Improve error handling"

5. **Troubleshooting**
   - "API returns 500 error"
   - "Database connection issues"
   - "Deployment failing"

6. **Best Practices**
   - "How to structure a Python project?"
   - "What's the best way to handle secrets?"
   - "How to write tests for FastAPI?"

### ❌ Not Appropriate For

- Mobile app development (iOS/Android native)
- Frontend-heavy React/Vue/Angular apps
- Real-time trading systems (<100ms latency)
- Enterprise Java/.NET systems

---

## Standard Process

### Phase 1: Requirements (5-10 min)

**Questions I Ask:**
```
1. What problem does this app solve?
2. Who are the users?
3. What are the core features?
4. What's your technical stack preference?
5. Where will it be deployed?
6. What's your timeline?
7. Any compliance requirements?
```

### Phase 2: Architecture Design (10-15 min)

**Deliverable:** Architecture diagram + tech stack

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │ ───► │   Backend   │ ───► │  Database   │
│  Streamlit  │      │   FastAPI   │      │  SQLite/PG  │
└─────────────┘      └─────────────┘      └─────────────┘
```

### Phase 3: Implementation (Ongoing)

**What I Provide:**
- Complete, working code
- Tests for critical paths
- Configuration files
- Deployment scripts
- Documentation

### Phase 4: Testing (5-10 min)

**Verification:**
```bash
# Run tests
pytest tests/ -v

# Test locally
uvicorn src.main:app --reload

# Check API docs
open http://localhost:8000/docs
```

### Phase 5: Deployment (10-15 min)

**Deploy to Production:**
```bash
./scripts/deploy-to-production.sh
```

### Phase 6: Monitoring (Ongoing)

**What I Monitor:**
- Health endpoints
- Error logs
- Performance metrics
- User feedback

---

## Output Templates

### Template 1: Project Structure

```
project-name/
├── src/
│   ├── main.py
│   ├── config.py
│   └── ...
├── tests/
├── scripts/
├── .env.example
├── requirements.txt
└── README.md
```

### Template 2: Deployment Script

```bash
#!/bin/bash
set -e

# Pre-deployment checks
./scripts/pre-deploy-check.sh

# Backup
./scripts/backup-database.sh

# Deploy
docker build -t app:latest .
docker stop app && docker rm app
docker run -d --name app -p 8000:8000 app:latest

# Health check
curl http://localhost:8000/health
```

### Template 3: API Endpoint

```python
@app.get("/api/v1/resource", response_model=ResourceResponse)
def get_resource(
    id: int,
    db: Session = Depends(get_db)
):
    """Get resource by ID"""
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Not found")
    return resource
```

---

## Quality Standards

### Code Quality
- ✅ Type hints on all functions
- ✅ Docstrings for public methods
- ✅ Error handling with proper HTTP codes
- ✅ Logging for debugging
- ✅ Tests for critical paths

### Security
- ✅ No hardcoded secrets
- ✅ Input validation
- ✅ SQL injection protection
- ✅ CORS configured
- ✅ Environment variables for config

### Documentation
- ✅ README with quick start
- ✅ API documentation (OpenAPI)
- ✅ Deployment guide
- ✅ Troubleshooting section
- ✅ Code comments (why, not what)

### Testing
- ✅ Unit tests (80%+ coverage)
- ✅ Integration tests
- ✅ Manual testing checklist
- ✅ CI/CD pipeline

---

## Continuous Learning

### Stay Updated On:
- FastAPI new features
- Streamlit components
- Cloud provider free tiers
- Deployment best practices
- Security vulnerabilities
- Python version updates

### Resources:
- FastAPI documentation
- Streamlit documentation
- Google Cloud docs
- GitHub Actions docs
- Python security advisories

---

## Handoff Protocol

### When to Escalate to Human Expert:
- Enterprise compliance (SOC2, HIPAA)
- Custom infrastructure needs
- Budget > $1000/month
- Multi-region deployment
- Complex networking (VPC peering)

### Information to Preserve:
- Architecture diagram
- Deployment history
- Known issues
- Configuration files
- Access credentials (never store, but verify setup)

---

**Skill Status:** ✅ Active
**Last Updated:** March 5, 2026
**Usage Count:** Ready for first app development
**Success Metrics:** Deployment success rate, code quality, user satisfaction
