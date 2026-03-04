"""
TA-DSS: Post-Trade Position Monitoring System

FastAPI application entry point.
"""

from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as positions_router
from src.api.schemas import HealthResponse, MessageResponse
from src.config import settings
from src.database import initialize_database
from src.scheduler import start_scheduler, stop_scheduler, get_scheduler_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events including:
    - Database initialization
    - Background scheduler startup
    - Graceful shutdown cleanup
    """
    # Startup: Initialize database
    initialize_database(verbose=True)
    
    # Start background scheduler
    start_scheduler()
    
    print(f"✓ Server starting on http://{settings.host}:{settings.port}")
    print(f"✓ Background scheduler running (interval={settings.monitor_interval / 3600}h)")

    yield

    # Shutdown: cleanup
    stop_scheduler()
    print("✓ Server shutting down...")


app = FastAPI(
    title="TA-DSS: Post-Trade Position Monitoring System",
    description="""
## Overview

A decision support system for monitoring trading positions with technical analysis.

## Features

* **Position Management** - Log and track manual trades
* **Technical Analysis** - RSI, MACD, EMA signals
* **Automated Monitoring** - Background scheduler checks positions
* **Telegram Alerts** - Real-time notifications on signal changes

## API Endpoints

### Positions
- `POST /positions/open` - Create a new position
- `GET /positions/open` - List all open positions
- `GET /positions` - List all positions (with filtering)
- `GET /positions/{id}` - Get specific position
- `POST /positions/{id}/close` - Close a position
- `DELETE /positions/{id}` - Delete a position

### Health
- `GET /health` - Health check
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(positions_router, prefix="/api/v1")


@app.get("/", response_model=MessageResponse, tags=["root"])
def root() -> MessageResponse:
    """
    Root endpoint with API information.

    Returns:
        Welcome message with documentation link.
    """
    return MessageResponse(
        message="Welcome to TA-DSS API",
        detail="Documentation available at /docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Current system status and timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
    )
