# One-Click Deployment Script for Oracle Cloud

**Script:** `scripts/deploy-oracle.sh`  
**Purpose:** Automated deployment of TA-DSS to Oracle Cloud Free Tier (ARM64)  
**Last Updated:** March 3, 2026

---

## Quick Start

```bash
# Navigate to project root
cd /path/to/trading-order-monitoring-system

# Run deployment script
./scripts/deploy-oracle.sh <your-oracle-cloud-ip>

# Example with default SSH key
./scripts/deploy-oracle.sh 129.146.123.45

# Example with custom SSH key
./scripts/deploy-oracle.sh 129.146.123.45 ~/.ssh/oracle-trading-key
```

---

## Prerequisites

### Local Machine (Your Computer)

| Requirement | How to Check | How to Install |
|-------------|--------------|----------------|
| **Docker** | `docker --version` | [Install Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | `docker compose version` | Included with Docker Desktop |
| **SSH Key** | `ls -la ~/.ssh/oracle-trading-key` | `ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle-trading-key` |
| **.env File** | `cat .env \| grep TELEGRAM` | `cp .env.example .env` and edit |

### Oracle Cloud VM

| Requirement | Status |
|-------------|--------|
| Ubuntu 22.04 LTS (ARM64) | ✅ Required |
| Public IP address | ✅ Required |
| SSH access (port 22) | ✅ Required |
| Security List: Port 22 open | ✅ Required |
| Security List: Port 8000 open | ⚠️ Deploy script will remind |
| Security List: Port 8503 open | ⚠️ Deploy script will remind |

---

## Step-by-Step Guide

### Step 1: Prepare Oracle Cloud VM

1. **Create VM Instance** in Oracle Cloud Console:
   - Shape: `VM.Standard.A1.Flex` (ARM)
   - OCPUs: 2
   - Memory: 12 GB
   - Image: Ubuntu 22.04 LTS
   - Add your SSH public key

2. **Note the Public IP** address assigned to the VM

3. **Test SSH Connection**:
   ```bash
   ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>
   ```

### Step 2: Configure .env File

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env
```

**Required Variables:**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### Step 3: Run Deployment Script

```bash
# Make script executable (if not already)
chmod +x scripts/deploy-oracle.sh

# Run deployment
./scripts/deploy-oracle.sh 129.146.123.45
```

### Step 4: Configure Oracle Cloud Security Lists

After deployment, open required ports:

1. Go to **Oracle Cloud Console** → **Networking** → **Virtual Cloud Networks**
2. Click your **VCN**
3. Click **Security Lists**
4. Add **Ingress Rules**:

| Source CIDR | Destination Port Range | Protocol | Description |
|-------------|------------------------|----------|-------------|
| 0.0.0.0/0 | 8000 | TCP | API Server |
| 0.0.0.0/0 | 8503 | TCP | Dashboard (optional) |

### Step 5: Verify Deployment

```bash
# Check from your browser
http://<your-oracle-ip>:8000/health
http://<your-oracle-ip>:8000/docs

# Or via SSH
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip> "docker ps"
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip> "curl http://localhost:8000/health"
```

---

## Script Output Example

```
[INFO] ╔══════════════════════════════════════════════════════════╗
[INFO] ║     TA-DSS Oracle Cloud Deployment Script                ║
[INFO] ╚══════════════════════════════════════════════════════════╝

[INFO] Target Server: 129.146.123.45
[INFO] SSH Key: /home/user/.ssh/oracle-trading-key
[INFO] SSH User: ubuntu

Continue with deployment? (y/N): y

═══════════════════════════════════════════════════════════
► Checking Prerequisites
═══════════════════════════════════════════════════════════

[INFO] Checking Docker installation...
[INFO] ✓ Docker installed: Docker version 24.0.7, build afdd53b
[INFO] Checking Docker Compose installation...
[INFO] ✓ Docker Compose installed: Docker Compose version v2.24.0
[INFO] Checking .env file...
[INFO] ✓ .env file found
[INFO] ✓ TELEGRAM_BOT_TOKEN configured
[INFO] ✓ TELEGRAM_CHAT_ID configured
[INFO] Checking SSH key...
[INFO] ✓ SSH key found: /home/user/.ssh/oracle-trading-key
[INFO] Testing connectivity to Oracle Cloud VM (129.146.123.45)...
[INFO] ✓ Oracle Cloud VM is reachable
[INFO] Testing SSH connectivity...
[INFO] ✓ SSH connection successful
[INFO] ✓ All prerequisites passed

═══════════════════════════════════════════════════════════
► Building Docker Images (ARM64)
═══════════════════════════════════════════════════════════

[INFO] Building Docker image for linux/arm64...
[+] Building 45.2s (15/15) FINISHED
...
[INFO] ✓ Docker image built successfully

Do you want to push the image to Oracle Container Registry? (y/N): n

═══════════════════════════════════════════════════════════
► Deploying to Oracle Cloud VM (129.146.123.45)
═══════════════════════════════════════════════════════════

[INFO] Creating remote directory...
[INFO] Copying files to server...
[INFO] ✓ Files copied successfully

═══════════════════════════════════════════════════════════
► Setting up Oracle Cloud VM
═══════════════════════════════════════════════════════════

[INFO] Executing setup script on server...
Installing Docker...
Installing Docker Compose...
Creating directories...
Setting permissions...
Building Docker image...
Starting services...
[INFO] ✓ Server setup complete

═══════════════════════════════════════════════════════════
► Verifying Deployment
═══════════════════════════════════════════════════════════

[INFO] Waiting for services to initialize...
[INFO] Checking container status...
[INFO] ✓ Health check passed
[INFO] ✓ Scheduler is running

═══════════════════════════════════════════════════════════
► Deployment Complete! Access Information
═══════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════╗
║          TA-DSS Deployment Successful!                  ║
╚══════════════════════════════════════════════════════════╝

Server: 129.146.123.45

Access URLs:
  • API Server:     http://129.146.123.45:8000
  • API Docs:       http://129.146.123.45:8000/docs
  • Health Check:   http://129.146.123.45:8000/health
  • Dashboard:      http://129.146.123.45:8503 (if enabled)

Useful Commands:
  # Check container status
  ssh -i ~/.ssh/oracle-trading-key ubuntu@129.146.123.45 "docker ps"
  
  # View logs
  ssh -i ~/.ssh/oracle-trading-key ubuntu@129.146.123.45 "docker compose logs -f"
  
  # Restart services
  ssh -i ~/.ssh/oracle-trading-key ubuntu@129.146.123.45 "docker compose restart"

Deployment completed at: Tue Mar 3 14:30:00 UTC 2026
```

---

## Troubleshooting

### "Docker not found"

Install Docker on your local machine:
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS
brew install --cask docker
```

### "SSH connection failed"

```bash
# Verify SSH key permissions
chmod 600 ~/.ssh/oracle-trading-key

# Test connection manually
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Check if public key is on VM
# (You may need to add it manually)
cat ~/.ssh/oracle-trading-key.pub | ssh ubuntu@<your-oracle-ip> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### "Health check failed"

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Check container status
docker ps

# View logs
docker compose logs -f tadss-api

# Restart services
docker compose restart
```

### "Port not accessible from browser"

1. Check Oracle Cloud Security Lists:
   - Go to VCN → Security Lists
   - Add ingress rule for port 8000 (and 8503 for dashboard)

2. Check UFW firewall on VM:
   ```bash
   ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>
   sudo ufw allow 8000/tcp
   sudo ufw allow 8503/tcp
   sudo ufw status
   ```

### "Docker Compose command not found"

The script tries both `docker compose` and `docker-compose`. If neither works:

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Install Docker Compose
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-aarch64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
```

---

## Manual Deployment (Alternative)

If the script fails, deploy manually:

### 1. SSH into Server

```bash
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>
```

### 2. Install Docker & Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-aarch64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

# Logout and login again for group changes to take effect
exit
```

### 3. Copy Files

```bash
# From local machine
scp -i ~/.ssh/oracle-trading-key -r docker/ ubuntu@<your-oracle-ip>:/opt/trading-monitor/
scp -i ~/.ssh/oracle-trading-key .env ubuntu@<your-oracle-ip>:/opt/trading-monitor/
scp -i ~/.ssh/oracle-trading-key requirements.txt ubuntu@<your-oracle-ip>:/opt/trading-monitor/
```

### 4. Build and Run

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Navigate to deploy directory
cd /opt/trading-monitor/docker

# Create data and logs directories
mkdir -p data logs

# Build image
docker build --platform linux/arm64 -t tadss:latest ..

# Start services
docker compose up -d

# Check status
docker ps
docker compose logs -f
```

---

## Post-Deployment Tasks

### 1. Test API

```bash
curl http://<your-oracle-ip>:8000/health
curl http://<your-oracle-ip>:8000/api/v1/positions/scheduler/status
```

### 2. Test Telegram Alert

```bash
curl -X POST http://<your-oracle-ip>:8000/api/v1/positions/scheduler/test-alert
```

### 3. View Logs

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f tadss-api
docker compose logs -f tadss-keepalive
```

### 4. Monitor Resources

```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Check memory
free -h
```

---

## Update Deployment

To update with new code:

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Navigate to deploy directory
cd /opt/trading-monitor/docker

# Pull latest changes (if using git)
cd ..
git pull

# Rebuild and restart
cd docker
docker compose down
docker build --platform linux/arm64 -t tadss:latest ..
docker compose up -d

# Verify
docker ps
curl http://localhost:8000/health
```

---

## Rollback

To rollback to previous version:

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Navigate to deploy directory
cd /opt/trading-monitor

# Checkout previous version
git checkout <previous-commit-hash>

# Rebuild and restart
cd docker
docker compose down
docker build --platform linux/arm64 -t tadss:latest ..
docker compose up -d
```

---

## Uninstall

To remove everything:

```bash
# SSH into server
ssh -i ~/.ssh/oracle-trading-key ubuntu@<your-oracle-ip>

# Stop and remove containers
cd /opt/trading-monitor/docker
docker compose down -v

# Remove images
docker rmi tadss:latest

# Remove deploy directory
cd ..
sudo rm -rf /opt/trading-monitor

# Remove Docker (optional)
sudo apt remove docker-ce docker-ce-cli containerd.io
sudo rm -rf /var/lib/docker
```

---

## Related Files

| File | Purpose |
|------|---------|
| `scripts/deploy-oracle.sh` | Main deployment script |
| `docker/Dockerfile` | ARM64 Docker image |
| `docker/docker-compose.yml` | Service orchestration |
| `docker/docker-entrypoint.sh` | Container initialization |
| `docker/keepalive.sh` | Idle prevention |
| `.env.example` | Environment template |

---

## Support

| Issue | Solution |
|-------|----------|
| Script fails at prerequisites | Check error message, install missing dependencies |
| Build fails on ARM64 | Ensure Oracle Cloud VM is ARM shape (VM.Standard.A1.Flex) |
| Services won't start | Check logs: `docker compose logs -f` |
| Can't access API | Check Oracle Cloud Security Lists and UFW firewall |

---

**Last Updated:** March 3, 2026  
**Version:** 1.0
