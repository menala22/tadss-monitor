#!/bin/bash
# =============================================================================
# Keep-Alive Script for Oracle Cloud Free Tier
# =============================================================================
# Prevents Oracle from reclaiming idle ARM64 instances
# Runs lightweight health checks every 30 minutes
# =============================================================================
# Usage: ./keepalive.sh
# Control: Set ENABLE_KEEPALIVE=true in environment to activate
# =============================================================================

set -e

# Configuration
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
INTERVAL_SECONDS="${KEEPALIVE_INTERVAL:-1800}"  # 30 minutes default
LOG_FILE="${KEEPALIVE_LOG_FILE:-/opt/app/logs/keepalive.log}"

# Colors for output (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        INFO)  echo -e "${GREEN}[$timestamp] [INFO]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[$timestamp] [WARN]${NC} $message" ;;
        ERROR) echo -e "${RED}[$timestamp] [ERROR]${NC} $message" ;;
        *)     echo "[$timestamp] $message" ;;
    esac
    
    # Also log to file if writable
    if [ -w "$(dirname "$LOG_FILE")" ]; then
        echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

# Health check function
check_health() {
    local response
    local http_code
    
    # Make health check request
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$HEALTH_URL" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        log "INFO" "✓ Health check passed (HTTP $http_code)"
        return 0
    else
        log "WARN" "✗ Health check failed (HTTP $http_code)"
        return 1
    fi
}

# Main loop
main() {
    log "INFO" "========================================="
    log "INFO" "Keep-Alive Script Started"
    log "INFO" "========================================="
    log "INFO" "Health URL: $HEALTH_URL"
    log "INFO" "Interval: $INTERVAL_SECONDS seconds ($(( INTERVAL_SECONDS / 60 )) minutes)"
    log "INFO" "Log File: $LOG_FILE"
    log "INFO" "========================================="
    
    # Initial health check
    log "INFO" "Running initial health check..."
    if ! check_health; then
        log "WARN" "Initial health check failed. Will retry on next interval."
    fi
    
    # Main keep-alive loop
    local iteration=0
    while true; do
        iteration=$((iteration + 1))
        log "INFO" "Keep-alive iteration #$iteration"
        
        # Perform health check
        if ! check_health; then
            log "WARN" "Service may not be ready yet. Will retry on next interval."
        fi
        
        # Sleep until next check
        log "INFO" "Sleeping for $INTERVAL_SECONDS seconds..."
        sleep "$INTERVAL_SECONDS"
    done
}

# Check if keep-alive is enabled
if [ "${ENABLE_KEEPALIVE,,}" = "true" ]; then
    log "INFO" "ENABLE_KEEPALIVE is set to true. Starting keep-alive loop..."
    main
else
    log "INFO" "ENABLE_KEEPALIVE is not set to 'true'. Keep-alive script disabled."
    log "INFO" "Set ENABLE_KEEPALIVE=true to enable automatic health checks."
fi
