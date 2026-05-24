"""
Job model — thêm access_token cho Phase 1 MVP.
Mỗi job được cấp một token ngẫu nhiên khi tạo.
Token này dùng để bảo vệ result/report endpoint.
"""

import secrets
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, DateTime, Enum, Float, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _utcnow():
    """UTC now - timezone aware datetime."""
    return datetime.now(timezone.utc)


class JobStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


# SQLAlchemy Enum type - dùng native_enum=False để hỗ trợ SQLite
# SQLite không có native ENUM type, nên sẽ lưu dưới dạng VARCHAR
SQLAlchemyJobStatus = Enum(
    JobStatus,
    name="jobstatus",
    native_enum=False,  # Lưu dưới dạng String thay vì native ENUM
    values_callable=lambda x: [e.value for e in x],
)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    access_token = Column(
        String(64),
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
        unique=True,
        index=True,
    )
    status = Column(
        SQLAlchemyJobStatus,
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    # Input data
    cv_s3_key = Column(String(512), nullable=True)
    jd_text = Column(Text, nullable=True)

    # Output data
    result_json = Column(JSON, nullable=True)          # fit score, skills, etc.
    report_s3_key = Column(String(512), nullable=True) # DOCX report path on S3

    # Metadata
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self):
        return f"<Job id={self.id} status={self.status}>"

    def is_accessible_with_token(self, token: str) -> bool:
        """So sánh token an toàn, tránh timing attack."""
        return secrets.compare_digest(self.access_token, token)
