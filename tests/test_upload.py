"""
Tests cho upload CV endpoint.

Kiểm tra:
- Upload file hợp lệ
- Upload file sai định dạng
- Upload file quá lớn
- Worker failure handling
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.models import Job


# ─── Helpers tạo file giả ─────────────────────────────────────────────────────

def make_pdf_bytes(size_kb: int = 10) -> bytes:
    """Tạo bytes giả có magic bytes của PDF."""
    header = b"%PDF-1.4 fake pdf content for testing\n"
    padding = b"0" * (size_kb * 1024 - len(header))
    return header + padding


def make_docx_bytes() -> bytes:
    """Tạo bytes giả cho DOCX (zip magic bytes)."""
    return b"PK\x03\x04" + b"\x00" * 100  # ZIP magic bytes


def make_exe_bytes() -> bytes:
    """Tạo bytes file exe giả."""
    return b"MZ\x90\x00" + b"\x00" * 100  # EXE magic bytes


class TestUploadCV:
    """
    Tests cho POST /upload/cv/{job_id}.
    
    Upload endpoint yêu cầu:
    - File PDF hoặc DOCX
    - Token hợp lệ
    - Job tồn tại
    """

    UPLOAD_ENDPOINT = "/upload/cv"

    def test_upload_valid_pdf(self, client: TestClient, pending_job: Job):
        """Upload PDF hợp lệ → 200."""
        pdf_bytes = make_pdf_bytes(size_kb=50)
        res = client.post(
            f"{self.UPLOAD_ENDPOINT}/{pending_job.id}",
            files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == pending_job.id
        assert data["status"] == "uploaded"
        assert "size_bytes" in data

    def test_upload_invalid_file_type_returns_400(
        self, client: TestClient, pending_job
    ):
        """Upload .exe → 400 Bad Request."""
        exe_bytes = make_exe_bytes()
        res = client.post(
            f"{self.UPLOAD_ENDPOINT}/{pending_job.id}",
            files={
                "file": ("malware.exe", io.BytesIO(exe_bytes), "application/octet-stream")
            },
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 400
        assert "Invalid file type" in res.json()["detail"]

    def test_upload_txt_file_rejected(self, client: TestClient, pending_job):
        """Upload .txt → 400 (chỉ accept PDF/DOCX)."""
        txt_bytes = b"This is a plain text resume\nSkills: Python, SQL"
        res = client.post(
            f"{self.UPLOAD_ENDPOINT}/{pending_job.id}",
            files={"file": ("resume.txt", io.BytesIO(txt_bytes), "text/plain")},
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 400

    def test_upload_requires_valid_token(self, client: TestClient, pending_job):
        """Upload với token sai → 403."""
        pdf_bytes = make_pdf_bytes()
        res = client.post(
            f"{self.UPLOAD_ENDPOINT}/{pending_job.id}",
            files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            params={"access_token": "wrong_token_xyz"},
        )
        assert res.status_code == 403

    def test_upload_to_nonexistent_job_returns_404(self, client: TestClient):
        """Upload cho job không tồn tại → 404."""
        fake_id = str(uuid.uuid4())
        pdf_bytes = make_pdf_bytes()
        res = client.post(
            f"{self.UPLOAD_ENDPOINT}/{fake_id}",
            files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            params={"access_token": "any_token"},
        )
        assert res.status_code == 404


class TestWorkerFailure:
    """
    Tests liên quan đến worker failure.
    Worker thất bại → job status = failed, error_message được lưu.
    """

    def test_failed_job_has_error_message(
        self, client: TestClient, failed_job
    ):
        """Job failed phải có error_message."""
        res = client.get(
            f"/jobs/{failed_job.id}/result",
            params={"access_token": failed_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None
        assert len(data["error_message"]) > 0

    def test_failed_job_result_is_none(self, client: TestClient, failed_job):
        """Job failed không có result data."""
        res = client.get(
            f"/jobs/{failed_job.id}/result",
            params={"access_token": failed_job.access_token},
        )
        assert res.json()["result"] is None

    def test_failed_job_report_returns_409(self, client: TestClient, failed_job):
        """Job failed không có report."""
        res = client.get(
            f"/jobs/{failed_job.id}/report",
            params={"access_token": failed_job.access_token},
        )
        assert res.status_code == 409
