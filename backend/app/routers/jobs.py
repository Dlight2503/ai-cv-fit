"""
Router: /jobs

Endpoints:
  POST   /jobs/              — tạo job mới, trả về job_id + access_token
  GET    /jobs/{job_id}      — lấy status (không cần token)
  GET    /jobs/{job_id}/result  — lấy result JSON (cần token)
  GET    /jobs/{job_id}/report  — download link DOCX (cần token)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
import uuid

from app.core.database import get_db
from app.models import Job, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    jd_text: str


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    access_token: str
    status: str


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: str
    created_at: str
    updated_at: str


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None


# ─── Helper ──────────────────────────────────────────────────────────────────

def _get_job_or_404(job_id: str, db: Session) -> Job:
    """Lấy job theo id, raise 404 nếu không tồn tại."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _verify_token(job: Job, access_token: str) -> None:
    """Xác minh token, raise 403 nếu sai."""
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="access_token is required to view this resource",
        )
    if not job.is_accessible_with_token(access_token):
        raise HTTPException(
            status_code=403,
            detail="Invalid access_token",
        )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/", response_model=JobCreateResponse, status_code=201)
def create_job(
    payload: JobCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Tạo job mới.
    Response chứa access_token — frontend phải lưu lại để
    dùng cho /result và /report.
    """
    job = Job(
        id=str(uuid.uuid4()),
        jd_text=payload.jd_text,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # TODO: enqueue Celery task
    # from app.tasks import process_job
    # process_job.delay(job.id)

    return JobCreateResponse(
        job_id=job.id,
        access_token=job.access_token,
        status=job.status.value,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Lấy trạng thái job. Không cần token vì chỉ trả về status, không có data nhạy cảm.
    """
    job = _get_job_or_404(job_id, db)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(
    job_id: str,
    access_token: str = Query(..., description="Token nhận được khi tạo job"),
    db: Session = Depends(get_db),
):
    """
    Lấy result JSON của job.
    Yêu cầu access_token hợp lệ.
    """
    job = _get_job_or_404(job_id, db)
    _verify_token(job, access_token)

    if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
        return JobResultResponse(
            job_id=job.id,
            status=job.status.value,
            result=None,
        )

    if job.status == JobStatus.FAILED:
        return JobResultResponse(
            job_id=job.id,
            status=job.status.value,
            result=None,
            error_message=job.error_message,
        )

    return JobResultResponse(
        job_id=job.id,
        status=job.status.value,
        result=job.result_json,
    )


@router.get("/{job_id}/report")
def get_job_report(
    job_id: str,
    access_token: str = Query(..., description="Token nhận được khi tạo job"),
    db: Session = Depends(get_db),
):
    """
    Lấy presigned URL hoặc redirect để download DOCX report.
    Yêu cầu access_token hợp lệ.
    """
    job = _get_job_or_404(job_id, db)
    _verify_token(job, access_token)

    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=409,
            detail=f"Report not ready. Current status: {job.status.value}",
        )

    if not job.report_s3_key:
        raise HTTPException(status_code=404, detail="Report file not found")

    # TODO: generate presigned S3 URL
    # from app.services.storage import get_presigned_url
    # url = get_presigned_url(job.report_s3_key)
    # return RedirectResponse(url)

    return {
        "job_id": job.id,
        "report_s3_key": job.report_s3_key,
        "message": "Integrate with storage service to generate presigned URL",
    }
