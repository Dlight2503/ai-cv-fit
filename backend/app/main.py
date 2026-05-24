"""
FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.jobs import router as jobs_router
from app.routers.upload import router as upload_router
from app.models import Base
from app.core.database import get_engine

app = FastAPI(
    title="AI CV Fit API",
    version="1.0.0",
    description="CV Scoring & Report Generation API",
)

# CORS — cho phép frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(jobs_router)
app.include_router(upload_router)


@app.on_event("startup")
def on_startup():
    """Auto-create tables khi dùng SQLite (dev local)."""
    import os
    if not os.environ.get("DATABASE_URL"):
        print("Creating tables for SQLite local development...")
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-cv-fit"}
