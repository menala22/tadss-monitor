# TA-DSS Docker Deployment Guide for Oracle Cloud Free Tier

**Optimized for:** Oracle Ampere A1 (ARM64) instances  
**Date:** March 3, 2026  
**Version:** 1.0  

---

## Quick Start

### Build and Run (Single Command)

```bash
# Navigate to docker directory
cd docker

# Build for ARM64
docker build --platform linux/arm64 -t tadss:latest ..

# Run with resource limits
docker run -d \
  --name tadss-api \
  --platform linux/arm64 \
  --memory="8g" \
  --cpus="2" \
  -p 8000:8000 \
  -v tadss-data:/opt/app/data \
  -v tadss-logs:/opt/app/logs \
  -e ENABLE_KEEPALIVE=true \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  --restart unless-stopped \
  tadss:latest
```

### Using Docker Compose (Recommended)

```bash
# Navigate to docker directory
cd docker

# Copy and configure environment file
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

## Docker Commands Reference

### Build Commands

```bash
# Build for ARM64 (Oracle Cloud)
docker build --platform linux/arm64 -t tadss:latest ..

# Build with no cache (fresh build)
docker build --platform linux/arm64 --no-cache -t tadss:latest ..

# Build specific stage
docker build --platform linux/arm64 --target builder -t tadss:builder ..
```

### Run Commands

```bash
# Run with resource limits (recommended for free tier)
docker run -d \
  --name tadss-api \
  --platform linux/arm64 \
  --memory="8g" \
  --cpus="2" \
  -p 8000:8000 \
  -v tadss-data:/opt/app/data \
  -v tadss-logs:/opt/app/logs \
  -e ENABLE_KEEPALIVE=true \
  -e APP_ENV=production \
  --restart unless-stopped \
  tadss:latest

# Run with .env file
docker run -d \
  --name tadss-api \
  --platform linux/arm64 \
  --memory="8g" \
  --cpus="2" \
  -p 8000:8000 \
  --env-file ../.env \
  --restart unless-stopped \
  tadss:latest
```

### Docker Compose Commands

```bash
# Start services
docker compose up -d

# Start with build
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f tadss-api

# Stop services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v

# Restart services
docker compose restart

# View running containers
docker compose ps

# View resource usage
docker stats
```

### Container Management

```bash
# View container logs
docker logs -f tadss-api
docker logs --tail 100 tadss-api

# Execute commands inside container
docker exec -it tadss-api bash
docker exec -it tadss-api python -m src.database init

# View container details
docker inspect tadss-api

# View resource usage
docker stats tadss-api

# Restart container
docker restart tadss-api

# Stop container
docker stop tadss-api

# Remove container
docker rm tadss-api
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | `987654321` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Application environment | `production` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MONITOR_INTERVAL` | Scheduler interval (seconds) | `14400` |
| `TIMEZONE` | Scheduler timezone | `UTC` |
| `ENABLE_KEEPALIVE` | Enable idle prevention | `false` |
| `KEEPALIVE_INTERVAL` | Keep-alive interval (seconds) | `1800` |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/positions.db` |

---

## Resource Limits

### Oracle Cloud Free Tier (ARM)

| Resource | Free Tier Limit | Recommended for TA-DSS |
|----------|-----------------|------------------------|
| **OCPUs** | 4 total | 2 CPUs |
| **RAM** | 24 GB total | 8 GB |
| **Boot Volume** | 200 GB total | 50 GB |

### Docker Resource Flags

```bash
# CPU and Memory limits
--memory="8g"     # 8 GB RAM limit
--cpus="2"        # 2 CPU cores limit

# For docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 8G
    reservations:
      cpus: '1.0'
      memory: 4G
```

---

## Volume Management

### Create Volumes

```bash
docker volume create tadss-data
docker volume create tadss-logs
```

### Inspect Volumes

```bash
docker volume inspect tadss-data
docker volume inspect tadss-logs
```

### Backup Database

```bash
# Stop container
docker stop tadss-api

# Backup database volume
docker run --rm \
  -v tadss-data:/source \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/positions-backup-$(date +%Y%m%d).tar.gz -C /source .

# Start container
docker start tadss-api
```

### Restore Database

```bash
# Stop container
docker stop tadss-api

# Restore database volume
docker run --rm \
  -v tadss-data:/target \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/positions-backup-YYYYMMDD.tar.gz -C /target

# Start container
docker start tadss-api
```

---

## Keep-Alive Configuration

### Enable Keep-Alive (Prevent Oracle Idle Reclamation)

```bash
# Via docker run
docker run -d \
  -e ENABLE_KEEPALIVE=true \
  -e KEEPALIVE_INTERVAL=1800 \
  ...

# Via docker-compose.yml (already enabled by default)
environment:
  - ENABLE_KEEPALIVE=true
  - KEEPALIVE_INTERVAL=1800
```

### Keep-Alive Script Details

- **Interval:** 30 minutes (configurable)
- **Endpoint:** `http://localhost:8000/health`
- **Log File:** `/opt/app/logs/keepalive.log`
- **Resource Usage:** Minimal (<10MB RAM, runs in background)

### View Keep-Alive Logs

```bash
# View keep-alive logs
docker exec tadss-api cat /opt/app/logs/keepalive.log

# Follow keep-alive logs
docker exec -it tadss-api tail -f /opt/app/logs/keepalive.log
```

---

## Troubleshooting

### Container Won't Start

```bash
# View logs
docker logs tadss-api

# Check if port is in use
docker exec tadss-api netstat -tlnp | grep 8000

# Test database initialization
docker exec -it tadss-api python -m src.database init
```

### High Memory Usage

```bash
# View resource usage
docker stats tadss-api

# If using >8GB, consider:
# 1. Reduce MONITOR_INTERVAL
# 2. Disable dashboard if not needed
# 3. Check for memory leaks in logs
```

### Keep-Alive Not Working

```bash
# Check if keep-alive is enabled
docker exec tadss-api env | grep KEEPALIVE

# View keep-alive logs
docker exec tadss-api cat /opt/app/logs/keepalive.log

# Test health endpoint manually
docker exec tadss-api curl -f http://localhost:8000/health
```

### Database Issues

```bash
# Check database file exists
docker exec tadss-api ls -la /opt/app/data/

# Initialize database manually
docker exec -it tadss-api python -m src.database init

# Backup and recreate
docker volume rm tadss-data
docker volume create tadss-data
docker compose up -d
```

---

## Production Checklist

- [ ] `.env` file configured with Telegram credentials
- [ ] Resource limits set (8GB RAM, 2 CPUs)
- [ ] Volumes created for data persistence
- [ ] Keep-alive enabled (`ENABLE_KEEPALIVE=true`)
- [ ] Restart policy set (`unless-stopped`)
- [ ] Health check configured
- [ ] Logs rotating (max 3 files, 10MB each)
- [ ] Database backup procedure in place
- [ ] Firewall rules configured (port 8000)
- [ ] Oracle Cloud security list updated

---

## Image Size Optimization

### Current Image Size

```bash
# Check image size
docker images tadss:latest

# Expected size: ~500-700MB (with pandas, numpy, ccxt)
```

### Reduce Image Size (Optional)

```dockerfile
# Use smaller base image
FROM --platform=linux/arm64 python:3.10-alpine

# Note: Alpine requires additional compilation steps for numpy/pandas
# May not be worth the complexity for this application
```

---

## Security Best Practices

1. **Non-root User:** Container runs as `appuser` (UID 1000)
2. **Read-only .env:** Environment file mounted as read-only
3. **No Privilege Escalation:** `NoNewPrivileges=true` in Dockerfile
4. **Private Temp:** `PrivateTmp=true` in Dockerfile
5. **Health Checks:** Automatic health monitoring enabled
6. **Log Rotation:** Prevents disk space exhaustion

---

## Related Files

- `docker/Dockerfile` - Multi-stage ARM64 build
- `docker/docker-compose.yml` - Service orchestration
- `docker/docker-entrypoint.sh` - Container initialization
- `docker/keepalive.sh` - Idle prevention script
- `.env.example` - Environment template

---

**Last Updated:** March 3, 2026  
**Next Review:** After deployment testing
