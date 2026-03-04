#!/bin/bash
# =============================================================================
# TA-DSS: One-Click Deployment Script for Oracle Cloud Free Tier
# =============================================================================
# Script: deploy-oracle.sh
# Purpose: Deploy Trading Order Monitoring System to Oracle Cloud (ARM64)
# Usage: ./deploy-oracle.sh <oracle-cloud-ip> [ssh-key-path]
# =============================================================================
# Requirements:
#   - Docker & Docker Compose installed locally (for building)
#   - SSH access to Oracle Cloud VM
#   - .env file configured with Telegram credentials
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default ports
API_PORT=8000
DASHBOARD_PORT=8503

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
DEPLOY_DIR="/opt/trading-monitor"

# Files to deploy
FILES_TO_DEPLOY=(
    "docker/docker-compose.yml"
    "docker/Dockerfile"
    "docker/docker-entrypoint.sh"
    "docker/keepalive.sh"
    ".env"
    "requirements.txt"
)

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

usage() {
    cat << EOF
Usage: $0 <oracle-cloud-ip> [ssh-key-path]

Deploy TA-DSS to Oracle Cloud Free Tier (ARM64)

Arguments:
    oracle-cloud-ip    Public IP address of your Oracle Cloud VM
    ssh-key-path       Path to SSH private key (default: ~/.ssh/oracle-trading-key)

Examples:
    $0 129.146.123.45
    $0 129.146.123.45 ~/.ssh/oracle-trading-key

Prerequisites:
    1. Oracle Cloud VM running Ubuntu 22.04 (ARM64)
    2. SSH key pair created and public key added to VM
    3. Ports 8000 and 8503 open in Oracle Cloud Security Lists
    4. .env file configured with Telegram credentials

EOF
    exit 1
}

# =============================================================================
# Prerequisites Check
# =============================================================================

check_prerequisites() {
    log_step "Checking Prerequisites"
    
    local errors=0
    
    # Check Docker
    log_info "Checking Docker installation..."
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version)
        log_info "✓ Docker installed: $docker_version"
    else
        log_error "✗ Docker not found. Please install Docker first."
        errors=$((errors + 1))
    fi
    
    # Check Docker Compose
    log_info "Checking Docker Compose installation..."
    if command -v docker compose &> /dev/null; then
        local compose_version=$(docker compose version)
        log_info "✓ Docker Compose installed: $compose_version"
    elif command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version)
        log_info "✓ Docker Compose installed: $compose_version"
        COMPOSE_CMD="docker-compose"
    else
        log_error "✗ Docker Compose not found. Please install Docker Compose first."
        errors=$((errors + 1))
    fi
    
    # Check .env file
    log_info "Checking .env file..."
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_info "✓ .env file found"
        
        # Check required variables
        if grep -q "TELEGRAM_BOT_TOKEN=your_bot_token_here" "$PROJECT_ROOT/.env" || \
           ! grep -q "TELEGRAM_BOT_TOKEN=" "$PROJECT_ROOT/.env"; then
            log_warn "TELEGRAM_BOT_TOKEN not configured in .env"
        else
            log_info "✓ TELEGRAM_BOT_TOKEN configured"
        fi
        
        if grep -q "TELEGRAM_CHAT_ID=your_chat_id_here" "$PROJECT_ROOT/.env" || \
           ! grep -q "TELEGRAM_CHAT_ID=" "$PROJECT_ROOT/.env"; then
            log_warn "TELEGRAM_CHAT_ID not configured in .env"
        else
            log_info "✓ TELEGRAM_CHAT_ID configured"
        fi
    else
        log_error "✗ .env file not found at $PROJECT_ROOT/.env"
        log_warn "Copy .env.example to .env and configure it:"
        echo "    cp $PROJECT_ROOT/.env.example $PROJECT_ROOT/.env"
        echo "    nano $PROJECT_ROOT/.env"
        errors=$((errors + 1))
    fi
    
    # Check SSH key
    log_info "Checking SSH key..."
    if [ -f "$SSH_KEY" ]; then
        log_info "✓ SSH key found: $SSH_KEY"
        chmod 600 "$SSH_KEY" 2>/dev/null || true
    else
        log_error "✗ SSH key not found: $SSH_KEY"
        log_warn "Generate SSH key with:"
        echo "    ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle-trading-key"
        errors=$((errors + 1))
    fi
    
    # Check Oracle Cloud IP connectivity
    log_info "Testing connectivity to Oracle Cloud VM ($ORACLE_IP)..."
    if ping -c 2 -W 5 "$ORACLE_IP" &> /dev/null; then
        log_info "✓ Oracle Cloud VM is reachable"
    else
        log_warn "✗ Cannot ping Oracle Cloud VM. Check IP address and firewall rules."
    fi
    
    # Check SSH connectivity
    log_info "Testing SSH connectivity..."
    if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$SSH_USER@$ORACLE_IP" "exit" 2>/dev/null; then
        log_info "✓ SSH connection successful"
    else
        log_error "✗ SSH connection failed"
        log_warn "Check:"
        echo "    - SSH key is correct: $SSH_KEY"
        echo "    - Public key is added to VM's ~/.ssh/authorized_keys"
        echo "    - Port 22 is open in Oracle Cloud Security Lists"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "Prerequisites check failed with $errors error(s)"
        exit 1
    fi
    
    log_info "✓ All prerequisites passed"
}

# =============================================================================
# Build Docker Images
# =============================================================================

build_images() {
    log_step "Building Docker Images (ARM64)"
    
    cd "$DOCKER_DIR"
    
    log_info "Building Docker image for linux/arm64..."
    docker build \
        --platform linux/arm64 \
        -t tadss:latest \
        -t tadss:arm64 \
        ..
    
    log_info "✓ Docker image built successfully"
    
    # Optional: Push to Oracle Container Registry
    echo ""
    read -p "Do you want to push the image to Oracle Container Registry? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        push_to_registry
    fi
}

push_to_registry() {
    log_step "Pushing to Oracle Container Registry"
    
    read -p "Enter Oracle Container Registry URL (e.g., ocir.region.oraclecloud.com/<namespace>): " OCR_URL
    if [ -z "$OCR_URL" ]; then
        log_warn "Skipping registry push"
        return
    fi
    
    read -p "Enter Docker auth token: " -s DOCKER_AUTH
    echo ""
    
    log_info "Tagging image..."
    docker tag tadss:latest "$OCR_URL/trading-monitor/tadss:latest"
    
    log_info "Logging in to registry..."
    echo "$DOCKER_AUTH" | docker login "$OCR_URL" --username '<your-username>' --password-stdin
    
    log_info "Pushing image..."
    docker push "$OCR_URL/trading-monitor/tadss:latest"
    
    log_info "✓ Image pushed to registry"
}

# =============================================================================
# Deploy to Oracle Cloud
# =============================================================================

deploy_to_server() {
    log_step "Deploying to Oracle Cloud VM ($ORACLE_IP)"
    
    # Create remote directory
    log_info "Creating remote directory..."
    ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "sudo mkdir -p $DEPLOY_DIR && sudo chown \$USER:\$USER $DEPLOY_DIR"
    
    # Copy files
    log_info "Copying files to server..."
    
    # Create temporary deploy directory
    TEMP_DEPLOY_DIR=$(mktemp -d)
    mkdir -p "$TEMP_DEPLOY_DIR/docker"
    mkdir -p "$TEMP_DEPLOY_DIR/data"
    mkdir -p "$TEMP_DEPLOY_DIR/logs"
    
    # Copy necessary files
    cp "$DOCKER_DIR/docker-compose.yml" "$TEMP_DEPLOY_DIR/docker/"
    cp "$DOCKER_DIR/Dockerfile" "$TEMP_DEPLOY_DIR/docker/"
    cp "$DOCKER_DIR/docker-entrypoint.sh" "$TEMP_DEPLOY_DIR/docker/"
    cp "$DOCKER_DIR/keepalive.sh" "$TEMP_DEPLOY_DIR/docker/"
    cp "$PROJECT_ROOT/.env" "$TEMP_DEPLOY_DIR/"
    cp "$PROJECT_ROOT/requirements.txt" "$TEMP_DEPLOY_DIR/"
    
    # Make scripts executable
    chmod +x "$TEMP_DEPLOY_DIR/docker/docker-entrypoint.sh"
    chmod +x "$TEMP_DEPLOY_DIR/docker/keepalive.sh"
    
    # Copy to server
    scp -i "$SSH_KEY" \
        -r "$TEMP_DEPLOY_DIR/"* \
        "$SSH_USER@$ORACLE_IP:$DEPLOY_DIR/"
    
    # Clean up temp directory
    rm -rf "$TEMP_DEPLOY_DIR"
    
    log_info "✓ Files copied successfully"
}

setup_server() {
    log_step "Setting up Oracle Cloud VM"
    
    # Create deployment script on server
    cat << 'EOF' > /tmp/deploy-setup.sh
#!/bin/bash
set -e

DEPLOY_DIR="/opt/trading-monitor"
cd $DEPLOY_DIR

echo "Installing Docker..."
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

echo "Installing Docker Compose..."
# Install Docker Compose
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-aarch64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

echo "Creating directories..."
mkdir -p data logs docker

echo "Setting permissions..."
chmod +x docker/docker-entrypoint.sh
chmod +x docker/keepalive.sh

echo "Building Docker image..."
cd docker
docker build --platform linux/arm64 -t tadss:latest ..

echo "Starting services..."
docker compose up -d

echo "Waiting for services to start..."
sleep 10

echo "Checking status..."
docker ps

echo ""
echo "Deployment complete!"
EOF

    # Copy setup script to server
    scp -i "$SSH_KEY" /tmp/deploy-setup.sh "$SSH_USER@$ORACLE_IP:~/deploy-setup.sh"
    
    # Execute setup script
    log_info "Executing setup script on server..."
    ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "chmod +x ~/deploy-setup.sh && ~/deploy-setup.sh"
    
    # Clean up
    ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "rm ~/deploy-setup.sh"
    rm /tmp/deploy-setup.sh
    
    log_info "✓ Server setup complete"
}

# =============================================================================
# Post-Deployment Verification
# =============================================================================

verify_deployment() {
    log_step "Verifying Deployment"
    
    # Wait for services to start
    log_info "Waiting for services to initialize..."
    sleep 15
    
    # Check container status
    log_info "Checking container status..."
    ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    
    # Health check
    log_info "Running health check..."
    HEALTH_RESPONSE=$(ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "curl -s http://localhost:$API_PORT/health")
    
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        log_info "✓ Health check passed"
        echo "  Response: $HEALTH_RESPONSE"
    else
        log_warn "✗ Health check failed or service not ready"
        echo "  Response: $HEALTH_RESPONSE"
    fi
    
    # Check scheduler status
    log_info "Checking scheduler status..."
    SCHEDULER_STATUS=$(ssh -i "$SSH_KEY" "$SSH_USER@$ORACLE_IP" "curl -s http://localhost:$API_PORT/api/v1/positions/scheduler/status")
    
    if echo "$SCHEDULER_STATUS" | grep -q "running"; then
        log_info "✓ Scheduler is running"
    else
        log_warn "Scheduler status unknown"
    fi
    
    echo ""
    log_info "✓ Deployment verification complete"
}

display_access_info() {
    log_step "Deployment Complete! Access Information"
    
    cat << EOF

${GREEN}╔══════════════════════════════════════════════════════════╗${NC}
${GREEN}║          TA-DSS Deployment Successful!                  ║${NC}
${GREEN}╚══════════════════════════════════════════════════════════╝${NC}

${CYAN}Server:${NC} $ORACLE_IP

${CYAN}Access URLs:${NC}
  • API Server:     http://$ORACLE_IP:$API_PORT
  • API Docs:       http://$ORACLE_IP:$API_PORT/docs
  • Health Check:   http://$ORACLE_IP:$API_PORT/health
  • Dashboard:      http://$ORACLE_IP:$DASHBOARD_PORT (if enabled)

${CYAN}Useful Commands:${NC}
  # Check container status
  ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "docker ps"
  
  # View logs
  ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "docker compose logs -f"
  
  # Restart services
  ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "docker compose restart"
  
  # Check scheduler
  ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "curl http://localhost:$API_PORT/api/v1/positions/scheduler/status"

${YELLOW}Important Notes:${NC}
  1. Ensure ports $API_PORT and $DASHBOARD_PORT are open in Oracle Cloud Console:
     - Go to Networking → Virtual Cloud Networks
     - Click your VCN → Security Lists
     - Add Ingress Rules for ports $API_PORT and $DASHBOARD_PORT
  
  2. Test Telegram alerts:
     ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "curl -X POST http://localhost:$API_PORT/api/v1/positions/scheduler/test-alert"
  
  3. Monitor keep-alive logs:
     ssh -i $SSH_KEY $SSH_USER@$ORACLE_IP "docker compose logs -f tadss-keepalive"

${GREEN}Deployment completed at: $(date)${NC}
EOF
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    # Parse arguments
    ORACLE_IP="${1:-}"
    SSH_KEY="${2:-$HOME/.ssh/oracle-trading-key}"
    SSH_USER="${SSH_USER:-ubuntu}"
    COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
    
    # Validate arguments
    if [ -z "$ORACLE_IP" ]; then
        log_error "Oracle Cloud IP address is required"
        usage
    fi
    
    echo ""
    log_info "╔══════════════════════════════════════════════════════════╗"
    log_info "║     TA-DSS Oracle Cloud Deployment Script                ║"
    log_info "╚══════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Target Server: $ORACLE_IP"
    log_info "SSH Key: $SSH_KEY"
    log_info "SSH User: $SSH_USER"
    echo ""
    
    # Confirm deployment
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    build_images
    deploy_to_server
    setup_server
    verify_deployment
    display_access_info
}

# Run main function
main "$@"
