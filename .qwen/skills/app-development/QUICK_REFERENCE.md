# App Development Skill - Quick Reference

**Skill:** `app-development`
**Use When:** Building Python/FastAPI applications with cloud deployment

---

## Quick Commands

### Project Setup
```bash
# Create project structure
mkdir -p src/{api,models,services,utils} tests scripts docs
touch src/main.py src/config.py requirements.txt .env.example
```

### Development
```bash
# Run locally
uvicorn src.main:app --reload --port 8001

# Run tests
pytest tests/ -v

# Run dashboard
streamlit run src/ui.py --server.port 8503
```

### Deployment
```bash
# Deploy to production
./scripts/deploy-to-production.sh

# Backup database
./scripts/backup-database.sh

# Rollback
./scripts/rollback.sh
```

---

## Common Patterns

### FastAPI Endpoint
```python
@app.get("/api/v1/resource")
def get_resource(id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(status_code=404)
    return resource
```

### SQLAlchemy Model
```python
class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

### Streamlit Dashboard
```python
st.title("Dashboard")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total", value=100)
st.dataframe(df)
```

### Docker Configuration
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Setup

### .env.example
```bash
DATABASE_URL=sqlite:///./data/app.db
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=change-me-in-production
```

### requirements.txt
```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
pydantic-settings>=2.1.0
streamlit>=1.54.0
python-telegram-bot>=22.6
```

---

## Deployment Platforms

| Platform | Cost | Best For |
|----------|------|----------|
| Google Cloud e2-micro | $0 | 24/7 VM, full control |
| Railway | ~$0.21/mo | Easy PaaS |
| GitHub Actions | FREE | Scheduled jobs |
| Hugging Face Spaces | FREE | Demos |

---

## Troubleshooting

### API Not Starting
```bash
# Check logs
docker logs app --tail 100

# Check port
lsof -ti:8000 | xargs kill -9

# Restart
docker restart app
```

### Database Issues
```bash
# Backup
./scripts/backup-database.sh

# Check schema
sqlite3 data/app.db ".schema"

# Migrate
alembic upgrade head
```

### Deployment Failed
```bash
# Rollback
./scripts/rollback.sh

# Check health
curl http://VM_IP:8000/health
```

---

## Testing Checklist

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] API docs load (`/docs`)
- [ ] Health endpoint works (`/health`)
- [ ] Database migrations work
- [ ] Environment variables set
- [ ] No secrets in code
- [ ] .env in .gitignore

---

## Security Checklist

- [ ] .env files not committed
- [ ] API keys in environment variables
- [ ] CORS configured
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak info
- [ ] Rate limiting on public endpoints
- [ ] HTTPS in production

---

**Last Updated:** March 5, 2026
