"""
conftest.py — Fixtures dùng chung cho toàn bộ test suite.

Dùng SQLite in-memory để test không cần PostgreSQL thật.
Mỗi test function có database riêng (isolation hoàn toàn).
"""

import sys
import os
from pathlib import Path

# Thêm backend/ vào sys.path để import được app
_backend_path = Path(__file__).parent.parent / "backend"
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))

import secrets
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, Job, JobStatus
from app.core.database import get_db

# ─── Import app (đã bao gồm routers từ main.py) ─────────────────────────────
from app.main import app


# ─── DB Fixtures ─────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///./test_temp.db"


@pytest.fixture(scope="function")
def db_engine():
    """Tạo engine SQLite in-memory cho mỗi test function."""
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Cấp một SQLAlchemy session dùng trong test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient với DB được override bằng test session.
    Mỗi request trong test sẽ dùng cùng một DB session.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session được đóng bởi db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Model Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_job(db_session: Session) -> Job:
    """Job ở trạng thái DONE với result và report sẵn sàng."""
    job = Job(
        id=str(uuid.uuid4()),
        status=JobStatus.DONE,
        jd_text="Backend engineer với 3 năm kinh nghiệm Python",
        result_json={
            "overall_fit_score": 82,
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "missing_skills": ["Kubernetes", "Terraform"],
            "strengths": ["Strong Python background", "API design experience"],
            "improvement_suggestions": ["Learn container orchestration"],
        },
        report_s3_key="reports/test-job-id/report.docx",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def pending_job(db_session: Session) -> Job:
    """Job mới tạo, chưa được xử lý."""
    job = Job(
        id=str(uuid.uuid4()),
        status=JobStatus.PENDING,
        jd_text="Frontend developer React",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def failed_job(db_session: Session) -> Job:
    """Job bị lỗi khi worker xử lý."""
    job = Job(
        id=str(uuid.uuid4()),
        status=JobStatus.FAILED,
        jd_text="Data scientist",
        error_message="LLM API timeout after 30s",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def processing_job(db_session: Session) -> Job:
    """Job đang được worker xử lý."""
    job = Job(
        id=str(uuid.uuid4()),
        status=JobStatus.PROCESSING,
        jd_text="DevOps engineer",
        cv_s3_key="cv/test-job-id/resume.pdf",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job
