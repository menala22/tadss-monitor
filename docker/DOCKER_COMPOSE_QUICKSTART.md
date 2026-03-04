# TA-DSS Docker Compose Quick Reference

**For Oracle Cloud Free Tier (ARM64)**

---

## Quick Start

```bash
# Navigate to docker directory
cd docker

# Create required directories
mkdir -p data logs

# Copy and configure environment
cp ../.env.example ../.env
nano ../.env  # Edit with your Telegram credentials

# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Check status
docker compose ps
```

---

## Services Overview

| Service | Platform | Memory | CPUs | Purpose |
|---------|----------|--------|------|---------|
| `tadss-api` | linux/arm64 | 8 GB | 2 | FastAPI + Scheduler |
| `tadss-keepalive` | linux/arm64 | 256 MB | 0.5 | Idle prevention |
| `tadss-dashboard` | linux/arm64 | 2 GB | 1 | Streamlit UI (optional) |

**Total Resource Usage:** ~10 GB RAM, 3.5 CPUs (with dashboard)  
**Free Tier Limit:** 24 GB RAM, 4 OCPUs ✅

---

## Commands Reference

### Start/Stop

```bash
# Start all services
docker compose up -d

# Start with rebuild
docker compose up -d --build

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data!)
docker compose down -v

# Restart services
docker compose restart

# Restart specific service
docker compose restart tadss-api
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f tadss-api
docker compose logs -f tadss-keepalive

# Last 100 lines
docker compose logs --tail=100 tadss-api

# With timestamps
docker compose logs -ft tadss-api
```

### Check Status

```bash
# Running containers
docker compose ps

# Detailed status
docker compose ps -a

# Resource usage
docker stats

# Service health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
```

### Execute Commands

```bash
# Shell inside API container
docker compose exec tadss-api bash

# Initialize database manually
docker compose exec tadss-api python -m src.database init

# Test health endpoint
docker compose exec tadss-api curl http://localhost:8000/health

# View environment
docker compose exec tadss-api env
```

---

## Volume Management

### Directories

| Volume | Host Path | Container Path | Purpose |
|--------|-----------|----------------|---------|
| `./data` | `docker/data/` | `/opt/app/data` | SQLite database |
| `./logs` | `docker/logs/` | `/opt/app/logs` | Application logs |

### Backup Database

```bash
# Stop services
docker compose down

# Backup database
tar czf positions-backup-$(date +%Y%m%d).tar.gz data/

# Restart services
docker compose up -d
```

### Restore Database

```bash
# Stop services
docker compose down

# Extract backup
tar xzf positions-backup-YYYYMMDD.tar.gz -C data/

# Restart services
docker compose up -d
```

---

## Environment Variables

### Required (in .env)

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Optional (defaults in docker-compose.yml)

```bash
APP_ENV=production
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
MONITOR_INTERVAL=14400
TZ=UTC
ENABLE_KEEPALIVE=true
KEEPALIVE_INTERVAL=1800
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs tadss-api

# Check .env file
cat ../.env

# Validate configuration
docker compose config
```

### High Memory Usage

```bash
# View resource usage
docker stats

# Stop dashboard if not needed
docker compose stop tadss-dashboard

# Or reduce memory limit in docker-compose.yml
```

### Keep-Alive Not Working

```bash
# Check keep-alive logs
docker compose logs tadss-keepalive

# Verify ENABLE_KEEPALIVE is true
docker compose exec tadss-keepalive env | grep KEEPALIVE

# Test health endpoint
docker compose exec tadss-keepalive curl http://tadss-api:8000/health
```

### Database Issues

```bash
# Check database file
ls -la data/

# Initialize database
docker compose exec tadss-api python -m src.database init

# View database
docker compose exec tadss-api sqlite3 /opt/app/data/positions.db ".tables"
```

---

## Production Checklist

- [ ] `.env` file configured
- [ ] `data/` and `logs/` directories created
- [ ] Resource limits appropriate for your instance
- [ ] `ENABLE_KEEPALIVE=true` (default)
- [ ] `TZ=UTC` for consistent scheduler timing
- [ ] Firewall rules configured (port 8000)
- [ ] Oracle Cloud security list updated
- [ ] Database backup procedure in place
- [ ] Logs monitored regularly

---

## Update Deployment

```bash
# Pull latest changes (if using git)
cd /opt/trading-monitor
git pull

# Rebuild and restart
docker compose down
docker compose up -d --build

# Verify
docker compose ps
docker compose logs -f
```

---

## Remove Everything

```bash
# Stop and remove all containers, networks
docker compose down

# Remove volumes (WARNING: deletes all data!)
docker compose down -v

# Remove images
docker rmi tadss-api tadss-keepalive

# Remove build cache
docker builder prune -a
```

---

**Last Updated:** March 3, 2026  
**Version:** 1.0
