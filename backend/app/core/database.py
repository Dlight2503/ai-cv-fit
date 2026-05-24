"""
Database engine + session factory.
Hỗ trợ PostgreSQL (production) và SQLite (development/testing).
Dùng DATABASE_URL từ environment variable.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

_env_db_url = os.environ.get(
    "DATABASE_URL",
    None  # Không có default, sẽ dùng SQLite
)

# ─── Fallback sang SQLite nếu không có PostgreSQL ──────────────────────────
# Điều này giúp chạy local mà không cần PostgreSQL

def _get_database_url() -> str:
    """Lấy database URL, fallback sang SQLite nếu cần."""
    if _env_db_url:
        url = _env_db_url
        # Convert postgres:// → postgresql:// (psycopg2)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    # Fallback: SQLite local (chỉ dùng cho dev!)
    print("WARNING: DATABASE_URL not set. Using SQLite for local development.")
    print("For production, set DATABASE_URL to PostgreSQL connection string.")
    return "sqlite:///./ai_cv_fit.db"


_engine = None
_SessionLocal = None


def get_engine():
    """Lazy initialization của engine (tránh import error khi không cần)."""
    global _engine
    if _engine is None:
        url = _get_database_url()
        if url.startswith("sqlite"):
            _engine = create_engine(url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session_local():
    """Lazy initialization của sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — cấp session cho mỗi request."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
