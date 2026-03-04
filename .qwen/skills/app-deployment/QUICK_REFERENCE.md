# App Deployment Agent - Quick Reference

**Version:** 1.0 | **Date:** March 4, 2026

---

## Quick Decision Tree

```
User wants to deploy app
    │
    ├─ "Need 24/7 uptime?"
    │   ├─ YES → "Budget?"
    │   │   ├─ $0 → Oracle Cloud Free Tier (ARM/x86)
    │   │   ├─ $5-10 → Railway or Vultr
    │   │   └─ $20+ → AWS/GCP/Azure
    │   │
    │   └─ NO (scheduled OK) → "How often?"
    │       ├─ Every few hours → GitHub Actions
    │       ├─ Daily → GitHub Actions or Cloud Run
    │       └─ On-demand → Cloud Run or Hugging Face
    │
    ├─ "What type of app?"
    │   ├─ API/Web Service → Cloud Run, Railway, VM
    │   ├─ Scheduled Job → GitHub Actions, Cloud Run
    │   ├─ Bot → Railway, VM, Hugging Face
    │   └─ ML/AI → Hugging Face Spaces
    │
    └─ "Technical level?"
        ├─ Beginner → Railway (easiest)
        ├─ Intermediate → GitHub Actions, Cloud Run
        └─ Advanced → VM, Kubernetes
```

---

## Platform Cheat Sheet

### GitHub Actions
```yaml
# Best for: Scheduled jobs, CI/CD
# Free: 2,000 min/month (public repos)

# Quick Setup:
# 1. Create .github/workflows/deploy.yml
# 2. Add secrets in repo settings
# 3. Push to trigger

# Limit: Max 6 hours per run
```

### Google Cloud Run
```bash
# Best for: Serverless APIs, on-demand
# Free: 2M requests/month

# Quick Deploy:
gcloud run deploy myapp \
  --source . \
  --allow-unauthenticated

# Add scheduler:
gcloud scheduler jobs create http daily-scan \
  --schedule "0 */4 * * *" \
  --uri https://myapp.run.app
```

### Oracle Cloud Free
```bash
# Best for: Full VM, 24/7 apps
# Free: Always (4 OCPU + 24GB ARM or 2× 1/8 OCPU x86)

# Create VM:
# Console → Compute → Instances → Create
# Shape: VM.Standard.A1.Flex (ARM) or E2.Micro (x86)

# Deploy:
ssh ubuntu@<IP>
sudo apt update
# ... install and run
```

### Hugging Face Spaces
```bash
# Best for: Docker apps, ML, demos
# Free: Unlimited (16 GB RAM)

# Quick Deploy:
# 1. Create Space at hf.co/new-space
# 2. Select Docker SDK
# 3. Push Dockerfile and code
# 4. Auto-deploys

# Note: Public by default
```

### Railway
```bash
# Best for: Low-maintenance apps
# Free: $5 credit/month (~500 hours)

# Quick Deploy:
npm i -g @railway/cli
railway login
railway init
railway up

# Cost: ~$0.15-5/month for typical apps
```

### Vultr
```bash
# Best for: Simple VM, predictable pricing
# Cost: $6/month (1 vCPU, 1 GB, 25 GB SSD)

# Deploy:
# Console → Deploy → Cloud Compute
# OS: Ubuntu 22.04
# Plan: $6/month

# SSH in:
ssh root@<IP>
```

---

## Cost Calculator

### Monthly Usage Estimation

```python
# Scheduled Jobs
runs_per_day = 6  # Every 4 hours
minutes_per_run = 3
days_per_month = 30

total_minutes = runs_per_day * minutes_per_run * days_per_month
# = 540 minutes/month

# GitHub Actions: 540 / 2000 = 27% of free tier ✅
# Cost: $0
```

### Platform Cost Comparison

| Monthly Runs | GitHub Actions | Cloud Run | Railway | Vultr |
|--------------|----------------|-----------|---------|-------|
| 180 (6/day) | FREE | FREE | ~$0.15 | $6 |
| 1,000 | FREE | FREE | ~$0.80 | $6 |
| 2,000 | FREE | FREE | ~$1.60 | $6 |
| 5,000 | $24 | FREE | ~$4 | $6 |
| 10,000 | $48 | FREE | ~$8 | $6 |

---

## Common Commands

### Docker
```bash
# Build
docker build -t myapp .

# Run locally
docker run -p 8000:8000 myapp

# Push to registry
docker tag myapp user/myapp:latest
docker push user/myapp:latest
```

### Kubernetes (Basic)
```bash
# Deploy
kubectl create deployment myapp --image=user/myapp:latest

# Expose
kubectl expose deployment myapp --port=80 --type=LoadBalancer

# Check status
kubectl get pods
kubectl get services
```

### systemd Service
```ini
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable
sudo systemctl enable myapp
sudo systemctl start myapp
sudo systemctl status myapp
```

---

## Environment Variable Templates

### Basic .env
```ini
# Application
APP_ENV=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# API Keys
API_KEY=your_api_key_here

# External Services
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-987654321
```

### Secure .env Handling
```bash
# Create
cat > .env << EOF
API_KEY=your_key_here
EOF

# Protect
chmod 600 .env

# Gitignore
echo ".env" >> .gitignore

# Load in app
from dotenv import load_dotenv
load_dotenv()
```

---

## Health Check Template

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/ready")
def ready():
    # Check database, external services
    try:
        # db.check()
        # redis.ping()
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}
```

---

## Troubleshooting Checklist

### App Won't Start
```
[ ] Check logs: docker logs <container> or journalctl -u app
[ ] Verify environment variables set
[ ] Check database connection string
[ ] Ensure port is not in use
[ ] Verify dependencies installed
```

### High Memory Usage
```
[ ] Check for memory leaks (profile app)
[ ] Reduce batch sizes
[ ] Add caching
[ ] Increase swap (VMs)
[ ] Upgrade plan if needed
```

### Timeouts
```
[ ] Optimize database queries
[ ] Add indexes
[ ] Implement caching (Redis)
[ ] Increase timeout limits
[ ] Break into smaller tasks
```

### Rate Limiting
```
[ ] Add delays between API calls
[ ] Implement exponential backoff
[ ] Use API key if available
[ ] Cache responses
[ ] Consider paid API tier
```

---

## Security Checklist

### Before Deploy
```
[ ] No hardcoded secrets in code
[ ] .env file in .gitignore
[ ] Database credentials rotated
[ ] Firewall rules configured
[ ] HTTPS enabled (if web app)
[ ] Dependencies up to date
[ ] Error messages don't leak info
```

### After Deploy
```
[ ] Change default passwords
[ ] Enable MFA (if available)
[ ] Set up monitoring/alerts
[ ] Configure log retention
[ ] Test backup/restore
[ ] Document access procedures
```

---

## Monitoring Commands

### Linux VM
```bash
# CPU/Memory
top
htop
free -h

# Disk
df -h
du -sh /var/log

# Logs
journalctl -u myapp -f
tail -f /var/log/myapp.log

# Network
netstat -tulpn
ss -tulpn
```

### Docker
```bash
# Container stats
docker stats

# Logs
docker logs -f <container>

# Inspect
docker inspect <container>
```

### Kubernetes
```bash
# Pod status
kubectl get pods

# Logs
kubectl logs -f <pod>

# Resource usage
kubectl top pods
```

---

## Deployment Checklist

### Pre-Deployment
```
[ ] Code reviewed and tested
[ ] Environment variables documented
[ ] Database migrations ready
[ ] Rollback plan prepared
[ ] Team notified (if production)
```

### During Deployment
```
[ ] Follow deployment guide
[ ] Monitor logs in real-time
[ ] Verify health checks pass
[ ] Test critical functionality
[ ] Document any issues
```

### Post-Deployment
```
[ ] All services healthy
[ ] Metrics look normal
[ ] No error spikes
[ ] Backups configured
[ ] Documentation updated
[ ] Team notified of completion
```

---

## Escalation Triggers

### Escalate to Senior Engineer When:
- Production outage > 30 minutes
- Data loss suspected
- Security breach suspected
- Compliance requirements unclear
- Budget exceeds authority
- Multi-team coordination needed

### Escalate to Management When:
- Budget > $1000/month
- Strategic platform decision
- Vendor contract needed
- Legal/compliance review required
- Major architecture change

---

**Quick Reference Version:** 1.0  
**Last Updated:** March 4, 2026  
**Maintained By:** App Deployment Agent Skill
