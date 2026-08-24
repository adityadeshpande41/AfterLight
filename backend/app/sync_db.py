"""Shared sync database URL and engine for tools that need synchronous access."""

from sqlalchemy import create_engine

from app.config import settings


def get_sync_url() -> str:
    """Build a psycopg2-compatible sync URL from the async DATABASE_URL."""
    url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    # Add sslmode for production (Render requires SSL)
    if "render.com" in url or "localhost" not in url:
        if "?" not in url:
            url += "?sslmode=require"
        elif "sslmode" not in url:
            url += "&sslmode=require"
    return url


SYNC_URL = get_sync_url()


def get_sync_engine():
    return create_engine(SYNC_URL)
