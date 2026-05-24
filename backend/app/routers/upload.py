"""
Router: /upload — xử lý upload CV file.

POST /upload/cv/{job_id}  — upload CV, lưu lên S3, trigger worker
"""

import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Job, JobStatus

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _verify_token(job: Job, access_token: str) -> None:
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="access_token is required",
        )
    if not job.is_accessible_with_token(access_token):
        raise HTTPException(
            status_code=403,
            detail="Invalid access_token",
        )


@router.post("/cv/{job_id}")
async def upload_cv(
    job_id: str,
    access_token: str = Query(..., description="Token nhận được khi tạo job"),
    file: UploadFile = File(..., description="CV file (PDF hoặc DOCX)"),
    db: Session = Depends(get_db),
):
    """
    Upload CV file cho một job.

    - Chỉ chấp nhận file PDF hoặc DOCX
    - Yêu cầu access_token hợp lệ
    - Lưu file lên S3 (Phase 1: lưu tạm)
    - Trigger worker xử lý job
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    _verify_token(job, access_token)

    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: PDF, DOCX",
        )

    # Read file content
    content = await file.read()

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content)} bytes. Max: {max_size} bytes",
        )

    # TODO: upload to S3 via storage service
    # from app.services.storage import upload_file
    # s3_key = f"cv/{job.id}/resume.pdf"
    # upload_file(s3_key, content, file.content_type)

    # Update job with CV key and status
    # job.cv_s3_key = s3_key
    # job.status = JobStatus.PROCESSING
    # db.commit()

    # TODO: enqueue Celery task
    # from app.tasks import process_job
    # process_job.delay(job.id)

    return {
        "job_id": job.id,
        "status": "uploaded",
        "filename": file.filename,
        "size_bytes": len(content),
        "content_type": file.content_type,
        "message": "CV uploaded successfully. Processing will begin shortly.",
    }
