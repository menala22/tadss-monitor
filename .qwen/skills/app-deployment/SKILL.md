# App Deployment Agent Skill

**Skill Name:** `app-deployment`  
**Version:** 1.0  
**Created:** March 4, 2026  
**Expertise Level:** Expert  

---

## Overview

Specialized AI agent for deploying applications to cloud platforms with focus on **free tier optimization**, **zero-downtime deployment**, and **production-ready configurations**.

---

## Core Capabilities

### 1. Platform Selection & Analysis

**What I Do:**
- Analyze application requirements (CPU, RAM, storage, network)
- Compare deployment platforms (free vs paid tiers)
- Recommend best fit based on budget, scalability, and maintenance needs
- Identify potential blockers (capacity issues, compatibility)

**Platforms I Know:**
| Platform | Free Tier | Best For |
|----------|-----------|----------|
| GitHub Actions | 2,000 min/month | Scheduled jobs, CI/CD |
| Google Cloud Run | 2M requests/month | Serverless APIs |
| Oracle Cloud Free | Always free (ARM/x86) | Full VM control |
| Hugging Face Spaces | Unlimited (16 GB RAM) | Docker apps, ML |
| Railway | $5 credit/month | Low-maintenance apps |
| Vultr | $6/month | Predictable VM pricing |
| Fly.io | Free allowance | Edge deployment |

---

### 2. Architecture Design

**What I Do:**
- Design deployment architecture (monolith vs microservices)
- Choose execution model (24/7 VM vs serverless vs scheduled)
- Plan data persistence strategy (database, file storage)
- Design networking (firewall, security groups, ingress rules)

**Architecture Patterns:**
```
Pattern 1: Serverless Scheduler (GitHub Actions)
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Cron       │ ───► │   Runner     │ ───► │   Telegram   │
│  Schedule    │      │   (Scan)     │      │   Alert      │
└──────────────┘      └──────────────┘      └──────────────┘
    Every 4h              3 min run            Instant
    Cost: FREE            Cost: FREE           Cost: FREE

Pattern 2: 24/7 VM (Oracle/Vultr)
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   VM         │ ───► │  Scheduler   │ ───► │   Telegram   │
│  Always On   │      │  (Internal)  │      │   Alert      │
└──────────────┘      └──────────────┘      └──────────────┘
    24/7                Every 4h             Instant
    Cost: $0-6/mo       Cost: Internal       Cost: FREE

Pattern 3: Serverless API (Cloud Run)
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Scheduler   │ ───► │   Container  │ ───► │   Telegram   │
│  (External)  │      │   (On-demand)│      │   Alert      │
└──────────────┘      └──────────────┘      └──────────────┘
    HTTP Trigger        Auto-scales          Instant
    Cost: FREE          Cost: FREE           Cost: FREE
```

---

### 3. Deployment Script Generation

**What I Do:**
- Create platform-specific deployment scripts
- Generate infrastructure-as-code (Terraform, CloudFormation)
- Write CI/CD pipeline configurations
- Create rollback procedures

**Deliverables:**
```yaml
# GitHub Actions Workflow
name: Deploy
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: ./deploy.sh

# Docker Compose
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"

# systemd Service
[Unit]
Description=My App
[Service]
ExecStart=/opt/app/start.sh
Restart=always
```

---

### 4. Environment Configuration

**What I Do:**
- Set up environment variables securely
- Configure secrets management
- Create `.env` templates
- Set up database connections

**Security Best Practices:**
```bash
# ✅ DO: Use secrets management
export API_KEY=$(aws secretsmanager get-secret-value ...)

# ❌ DON'T: Hardcode credentials
export API_KEY="sk-1234567890abcdef"

# ✅ DO: Use .env files (gitignored)
cat .env >> .gitignore
echo ".env" >> .gitignore

# ✅ DO: Set secure permissions
chmod 600 .env
```

---

### 5. Monitoring & Logging Setup

**What I Do:**
- Configure application logging
- Set up health check endpoints
- Create monitoring dashboards
- Configure alert notifications

**Standard Monitoring Stack:**
```python
# Health endpoint
@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Structured logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics endpoint (optional)
@app.get("/metrics")
def metrics():
    return {
        "uptime": get_uptime(),
        "requests": request_count,
        "errors": error_count
    }
```

---

### 6. Troubleshooting & Optimization

**What I Do:**
- Diagnose deployment failures
- Optimize resource usage
- Reduce costs (free tier maximization)
- Scale applications

**Common Issues & Fixes:**

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| OOM Killed | Memory > limit | Add swap, optimize code, upgrade plan |
| Timeout | Execution > limit | Optimize queries, add caching |
| Rate Limited | API calls too fast | Add delays, use backoff |
| Port Blocked | Firewall misconfigured | Check security groups, UFW rules |
| Secrets Missing | Env vars not set | Verify secrets configuration |

---

## When to Use This Skill

### ✅ Appropriate Use Cases

1. **New Application Deployment**
   - "How do I deploy my Python app to the cloud?"
   - "What's the cheapest way to run this 24/7?"
   - "Help me set up automated deployments"

2. **Platform Migration**
   - "Move from Heroku to free alternative"
   - "Migrate from VM to serverless"
   - "Switch cloud providers"

3. **Cost Optimization**
   - "Reduce my cloud bill"
   - "Maximize free tier usage"
   - "Compare hosting costs"

4. **Architecture Review**
   - "Is this setup production-ready?"
   - "How should I structure my deployment?"
   - "Review my deployment strategy"

5. **Troubleshooting**
   - "My app keeps crashing on deploy"
   - "Getting memory errors"
   - "Deployment fails silently"

### ❌ Not Appropriate For

- Simple static website hosting (use Netlify/Vercel guides)
- Mobile app deployment (App Store/Play Store specific)
- On-premise enterprise deployments (requires site survey)
- Real-time trading systems requiring <100ms latency

---

## Standard Process

### Phase 1: Requirements Gathering (5-10 min)

**Questions I Ask:**
```
1. What type of application is it? (API, scheduler, web app, bot)
2. What's your monthly budget? (Free, $5-10, $20+)
3. Does it need to run 24/7 or on schedule?
4. What's your expected traffic/usage?
5. Do you have a preferred cloud provider?
6. What's your technical comfort level? (CLI, GUI, managed)
7. Any compliance requirements? (GDPR, HIPAA, etc.)
```

### Phase 2: Platform Recommendation (5 min)

**Deliverable:** Comparison table with recommendation

```markdown
| Platform | Cost | Setup | Maintenance | Fit |
|----------|------|-------|-------------|-----|
| Option A | $X/mo | Easy | Low | 85% |
| Option B | $Y/mo | Medium | Medium | 90% ← Recommended |
| Option C | $Z/mo | Hard | High | 70% |

**Recommendation:** Option B because...
```

### Phase 3: Deployment Plan (10-15 min)

**Deliverable:** Step-by-step deployment guide

```markdown
## Deployment Steps

### Prerequisites
- [ ] Account created
- [ ] CLI installed
- [ ] Code ready

### Phase 1: Infrastructure
1. Create resource
2. Configure networking
3. Set up database

### Phase 2: Application
1. Deploy code
2. Configure environment
3. Run migrations

### Phase 3: Verification
1. Health check
2. Test critical paths
3. Monitor logs
```

### Phase 4: Implementation Support (Ongoing)

**What I Provide:**
- Copy-paste commands
- Configuration file templates
- Troubleshooting assistance
- Optimization suggestions

### Phase 5: Post-Deployment (5 min)

**Deliverable:** Operations checklist

```markdown
## Post-Deployment Checklist

### Immediate (Day 1)
- [ ] Health endpoint responding
- [ ] Logs flowing
- [ ] Alerts configured

### First Week
- [ ] Monitor error rates
- [ ] Check resource usage
- [ ] Verify backups

### Ongoing
- [ ] Weekly: Review logs
- [ ] Monthly: Check costs
- [ ] Quarterly: Security updates
```

---

## Output Templates

### Template 1: Deployment Guide

```markdown
# [App Name] Deployment Guide

## Overview
- **Platform:** [Provider]
- **Cost:** $X/month
- **Setup Time:** Y minutes
- **Maintenance:** Low/Medium/High

## Architecture
[Diagram or description]

## Prerequisites
- [List]

## Steps
1. [Step 1]
2. [Step 2]
...

## Verification
- [Check 1]
- [Check 2]

## Troubleshooting
| Issue | Solution |
|-------|----------|
| ... | ... |
```

### Template 2: Configuration Files

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - ENV=production
    ports:
      - "8000:8000"

# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: ./deploy.sh
```

### Template 3: Cost Analysis

```markdown
## Cost Breakdown

### Current Setup
| Resource | Usage | Cost |
|----------|-------|------|
| Compute | X hrs | $Y |
| Storage | Z GB | $W |
| Network | N GB | $M |
| **Total** | | **$TOTAL/mo** |

### Optimized Setup
| Change | Savings |
|--------|---------|
| Right-size VM | -$X/mo |
| Use spot instances | -$Y/mo |
| Enable caching | -$Z/mo |
| **New Total** | **$NEW/mo** |

**Savings:** $DIFF/month ($DIFF×12/year)
```

---

## Knowledge Base

### Cloud Provider Free Tiers (2026)

| Provider | Free Tier | Duration | Credit Card |
|----------|-----------|----------|-------------|
| GitHub Actions | 2,000 min/month | Unlimited | No (public repos) |
| Google Cloud Run | 2M requests | Unlimited | Yes |
| Oracle Cloud | 4 OCPU + 24GB | Unlimited | Yes |
| AWS Lambda | 1M requests | Unlimited | Yes |
| Hugging Face | 16 GB RAM | Unlimited | No |
| Railway | $5 credit | Monthly trial | Yes |
| Fly.io | Allowance | Unlimited | Yes |

### Common Tech Stacks

**Python FastAPI:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

**Node.js Express:**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
CMD ["node", "server.js"]
```

**Scheduled Jobs:**
```yaml
# GitHub Actions
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
```

---

## Examples

### Example 1: Python Scheduler Deployment

**User Request:**
> "I have a Python script that scans stock prices every 4 hours and sends Telegram alerts. How do I deploy this for free?"

**My Response:**
1. **Analyze Requirements:**
   - Schedule: Every 4 hours (6 runs/day)
   - Runtime: ~5 minutes per run
   - Monthly usage: 6 × 5 × 30 = 900 minutes
   - Budget: Free

2. **Recommend GitHub Actions:**
   - Free tier: 2,000 minutes/month
   - Usage: 900 minutes (45% of limit)
   - Setup: 30 minutes

3. **Provide Complete Guide:**
   - Workflow file
   - Script template
   - Secrets setup
   - Testing instructions

4. **Include Contingency:**
   - What to do if limit exceeded
   - Alternative platforms
   - Optimization tips

### Example 2: API Migration

**User Request:**
> "My Heroku free tier is ending. Where can I migrate my FastAPI app?"

**My Response:**
1. **Compare Alternatives:**
   | Platform | Cost | Migration Effort |
   |----------|------|------------------|
   | Railway | ~$5/mo | Low |
   | Cloud Run | FREE | Medium |
   | Oracle VM | FREE | High |

2. **Recommend Cloud Run** (best free option)

3. **Provide Migration Steps:**
   - Dockerize app
   - Deploy to Cloud Run
   - Configure Cloud Scheduler
   - Update DNS

---

## Quality Standards

### Documentation Quality
- ✅ Step-by-step instructions
- ✅ Copy-paste commands
- ✅ Expected output shown
- ✅ Troubleshooting included
- ✅ Security best practices

### Code Quality
- ✅ Production-ready examples
- ✅ Error handling included
- ✅ Environment variables for config
- ✅ Logging configured
- ✅ Health checks implemented

### Cost Transparency
- ✅ All costs clearly stated
- ✅ Free tier limits documented
- ✅ Overage charges explained
- ✅ Optimization suggestions provided

---

## Continuous Learning

### Stay Updated On:
- New cloud provider free tiers
- Pricing changes
- New deployment platforms
- Best practices (security, performance)
- Tool updates (Docker, Kubernetes, etc.)

### Resources:
- Cloud provider documentation
- DevOps communities (r/devops, DevOps subreddit)
- Industry blogs (AWS, Google Cloud, Azure)
- GitHub trending (deployment tools)

---

## Handoff Protocol

### When to Escalate to Human Expert:
- Enterprise compliance requirements (SOC2, HIPAA)
- Custom infrastructure needs
- Budget > $1000/month
- Multi-region deployment
- Complex networking (VPC peering, etc.)

### Information to Preserve:
- Current architecture diagram
- Deployment history
- Known issues
- Configuration files
- Access credentials (never store, but verify setup)

---

**Skill Status:** ✅ Active  
**Last Updated:** March 4, 2026  
**Usage Count:** Ready for first deployment  
**Success Metrics:** Deployment success rate, cost savings achieved, user satisfaction
