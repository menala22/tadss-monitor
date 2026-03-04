# Deployment Templates Collection

**Purpose:** Ready-to-use templates for common deployment scenarios  
**Version:** 1.0 | **Date:** March 4, 2026

---

## Template Index

### 1. GitHub Actions Workflows
- [Scheduled Job](#scheduled-job-every-4-hours)
- [Manual Trigger](#manual-trigger)
- [On Push Deployment](#on-push-deployment)

### 2. Docker Configurations
- [Python FastAPI](#python-fastapi-dockerfile)
- [Node.js Express](#nodejs-express-dockerfile)
- [Multi-stage Build](#multi-stage-build)

### 3. Infrastructure as Code
- [Docker Compose](#docker-compose)
- [systemd Service](#systemd-service)
- [Kubernetes Deployment](#kubernetes-deployment)

### 4. Cloud-Specific
- [Google Cloud Run](#google-cloud-run)
- [Railway](#railway)
- [Oracle Cloud VM](#oracle-cloud-vm-setup)

---

## GitHub Actions Workflows

### Scheduled Job (Every 4 Hours)

```yaml
name: TA-DSS Signal Scan

on:
  schedule:
    - cron: '10 */4 * * *'  # Every 4 hours at minute 10
  workflow_dispatch:  # Allow manual trigger

jobs:
  scan:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run scan
        run: python scan_and_alert.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      
      - name: Upload results (optional)
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: scan-results
          path: scan_results_*.json
          retention-days: 7
```

### Manual Trigger

```yaml
name: Manual Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'production'
        type: choice
        options:
          - production
          - staging

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Deploy
        run: ./deploy.sh
        env:
          API_KEY: ${{ secrets.API_KEY }}
```

### On Push Deployment

```yaml
name: Auto Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/app
            git pull
            docker-compose up -d --build
```

---

## Docker Configurations

### Python FastAPI Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js Express Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Expose port
EXPOSE 3000

# Run application
CMD ["node", "server.js"]
```

### Multi-stage Build (Python)

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

# Add to PATH
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Infrastructure as Code

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - db
    restart: unless-stopped
  
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=app
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### systemd Service

```ini
[Unit]
Description=My Application
Documentation=https://github.com/user/repo
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/myapp
Environment="PATH=/opt/myapp/venv/bin"
ExecStart=/opt/myapp/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
```

**Usage:**
```bash
# Install
sudo cp myapp.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable myapp
sudo systemctl start myapp

# Check status
sudo systemctl status myapp

# View logs
sudo journalctl -u myapp -f
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: user/myapp:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

---

## Cloud-Specific Templates

### Google Cloud Run

**Deploy Command:**
```bash
gcloud run deploy myapp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars ENV=production
```

**Add Cloud Scheduler:**
```bash
gcloud scheduler jobs create http myapp-schedule \
  --schedule "*/4 * * * *" \
  --http-method POST \
  --uri "https://myapp-xyz.run.app" \
  --headers "Authorization=Bearer $(gcloud auth print-identity-token)"
```

### Railway

**railway.json:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Deploy Commands:**
```bash
# Install CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# Add environment variables
railway variables set TELEGRAM_BOT_TOKEN=xxx
```

### Oracle Cloud VM Setup

**Cloud-init Script:**
```yaml
#cloud-config
package_update: true
packages:
  - python3
  - python3-pip
  - python3-venv
  - git

users:
  - name: ubuntu
    ssh_authorized_keys:
      - ssh-rsa AAAA... your_public_key

runcmd:
  - sudo -u ubuntu bash -c 'cd /opt && git clone <repo>'
  - sudo -u ubuntu bash -c 'cd /opt/app && python3 -m venv venv'
  - sudo -u ubuntu bash -c 'cd /opt/app && source venv/bin/activate && pip install -r requirements.txt'

write_files:
  - path: /etc/systemd/system/myapp.service
    content: |
      [Unit]
      Description=My App
      [Service]
      ExecStart=/opt/app/venv/bin/python main.py
      Restart=always
      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

runcmd:
  - systemctl daemon-reload
  - systemctl enable myapp
  - systemctl start myapp
```

---

## Environment Variable Templates

### Production .env.example
```ini
# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
APP_ENV=production
LOG_LEVEL=INFO
DEBUG=false

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=postgresql://user:password@host:5432/dbname
DATABASE_POOL_SIZE=5

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# API Keys
STRIPE_SECRET_KEY=sk_live_...
SENDGRID_API_KEY=SG....

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_PER_MINUTE=60
```

---

## Health Check Templates

### FastAPI Health Check
```python
from fastapi import FastAPI, HTTPException
from datetime import datetime
import psutil

app = FastAPI()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/ready")
async def ready():
    """Check if app is ready to serve traffic"""
    try:
        # Check database connection
        # Check external services
        # Check disk space
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Application metrics"""
    return {
        "memory_percent": psutil.Process().memory_percent(),
        "cpu_percent": psutil.Process().cpu_percent(),
        "uptime": datetime.utcnow().timestamp() - start_time
    }
```

---

## Monitoring Templates

### Log Rotation Config
```bash
# /etc/logrotate.d/myapp
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload myapp > /dev/null 2>&1 || true
    endscript
}
```

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

---

## Backup Scripts

### Database Backup
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/myapp"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Backup database
pg_dump $DATABASE_URL > $BACKUP_DIR/db_$DATE.sql

# Backup files
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/app/data

# Clean old backups
find $BACKUP_DIR -name "*.sql" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

**Add to crontab:**
```bash
# Daily backup at 2 AM
0 2 * * * /opt/myapp/backup.sh >> /var/log/backup.log 2>&1
```

---

## Rollback Scripts

### Docker Rollback
```bash
#!/bin/bash
# rollback.sh

# Get previous image
PREVIOUS_IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" | head -2 | tail -1)

echo "Rolling back to: $PREVIOUS_IMAGE"

# Stop current
docker-compose down

# Start previous
docker run -d $PREVIOUS_IMAGE

echo "Rollback complete"
```

### Git Rollback
```bash
#!/bin/bash
# git-rollback.sh

# Get previous commit
PREVIOUS_COMMIT=$(git rev-parse HEAD~1)

echo "Rolling back to: $PREVIOUS_COMMIT"

# Checkout previous
git checkout $PREVIOUS_COMMIT

# Redeploy
./deploy.sh

echo "Rollback complete"
```

---

**Template Collection Version:** 1.0  
**Last Updated:** March 4, 2026  
**Usage:** Copy and customize for your deployment needs
