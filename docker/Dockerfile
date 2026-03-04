# =============================================================================
# TA-DSS: Trading Order Monitoring System
# Multi-stage Dockerfile for Oracle Cloud Free Tier (ARM64)
# =============================================================================
# Optimized for Oracle Ampere A1 (ARM64) instances
# Platform: linux/arm64
# Base Image: python:3.10-slim-bullseye
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build Environment
# -----------------------------------------------------------------------------
FROM --platform=linux/arm64 python:3.10-slim-bullseye AS builder

# Install build dependencies required for compiling numpy/pandas on ARM
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libblas-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (will compile numpy/pandas for ARM)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production Runtime
# -----------------------------------------------------------------------------
FROM --platform=linux/arm64 python:3.10-slim-bullseye AS production

# Optimized for Oracle Ampere A1 (ARM64) instances

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /opt/app

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup data/ ./data/
COPY --chown=appuser:appgroup logs/ ./logs/

# Copy keep-alive script
COPY --chown=appuser:appgroup docker/keepalive.sh /usr/local/bin/keepalive.sh
RUN chmod +x /usr/local/bin/keepalive.sh

# Create directories with proper permissions
RUN mkdir -p /opt/app/data /opt/app/logs && \
    chown -R appuser:appgroup /opt/app

# Switch to non-root user
USER appuser

# Expose ports
# 8000: FastAPI server
# 8503: Streamlit dashboard (optional)
EXPOSE 8000 8503

# Environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    ENABLE_KEEPALIVE=false \
    DATABASE_URL=sqlite:///./data/positions.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entry point script
COPY --chown=appuser:appgroup docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command: run FastAPI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
