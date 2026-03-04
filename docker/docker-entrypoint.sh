#!/bin/bash
# =============================================================================
# Docker Entry Point Script for TA-DSS
# =============================================================================
# Handles initialization, database setup, and optional keep-alive process
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Initialization
# =============================================================================

log_info "========================================="
log_info "TA-DSS Docker Container Starting"
log_info "========================================="
log_info "Environment: $APP_ENV"
log_info "Host: $HOST"
log_info "Port: $PORT"
log_info "Database: $DATABASE_URL"
log_info "Keep-Alive: $ENABLE_KEEPALIVE"
log_info "========================================="

# Create necessary directories
log_info "Creating directories..."
mkdir -p /opt/app/data /opt/app/logs

# Set proper permissions
chown -R appuser:appgroup /opt/app 2>/dev/null || true

# =============================================================================
# Database Initialization
# =============================================================================

log_info "Checking database..."
if [ "$DATABASE_URL" == "sqlite:///./data/positions.db" ]; then
    if [ ! -f "/opt/app/data/positions.db" ]; then
        log_info "Initializing SQLite database..."
        python -m src.database init || log_warn "Database initialization may have already run"
    else
        log_info "Database already exists, skipping initialization"
    fi
else
    log_info "Using external database: $DATABASE_URL"
fi

# =============================================================================
# Keep-Alive Process (Optional)
# =============================================================================

if [ "${ENABLE_KEEPALIVE,,}" = "true" ]; then
    log_info "Starting keep-alive background process..."
    /usr/local/bin/keepalive.sh &
    KEEPALIVE_PID=$!
    log_info "Keep-alive PID: $KEEPALIVE_PID"
else
    log_info "Keep-alive disabled (set ENABLE_KEEPALIVE=true to enable)"
fi

# =============================================================================
# Start Main Application
# =============================================================================

log_info "========================================="
log_info "Starting FastAPI Server"
log_info "========================================="
log_info "API will be available at: http://$HOST:$PORT"
log_info "API Documentation: http://$HOST:$PORT/docs"
log_info "Health Check: http://$HOST:$PORT/health"
log_info "========================================="

# Execute the main command (passed from CMD or docker-compose)
exec "$@"
