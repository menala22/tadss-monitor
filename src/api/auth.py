"""
API key authentication dependency.

If API_SECRET_KEY is set in .env, all /api/v1/* endpoints require the
X-API-Key header to match. If the key is not configured (dev mode),
authentication is skipped.
"""

from fastapi import Header, HTTPException, status

from src.config import settings


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """
    FastAPI dependency that enforces API key authentication.

    - If settings.api_secret_key is None/empty: auth is disabled (dev mode).
    - If configured: X-API-Key header must be present and match exactly.

    Raises:
        HTTPException 401: If the key is missing or wrong.
    """
    if not settings.api_secret_key:
        return  # Auth disabled — no key configured

    if x_api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
