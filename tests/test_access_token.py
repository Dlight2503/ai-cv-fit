"""
Tests cho access token MVP.

Bao gồm tất cả cases được yêu cầu trong Phase 1:
- valid token
- bad token
- missing token
- bad job id
- missing report
"""

import secrets
import uuid
import pytest
from fastapi.testclient import TestClient

from app.models import Job, JobStatus


class TestAccessTokenResult:
    """Tests cho GET /jobs/{job_id}/result với access token."""

    def test_valid_token_returns_result(self, client: TestClient, sample_job: Job):
        """Token đúng → trả về result JSON."""
        res = client.get(
            f"/jobs/{sample_job.id}/result",
            params={"access_token": sample_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "done"
        assert data["result"] is not None
        assert "overall_fit_score" in data["result"]
        assert data["result"]["overall_fit_score"] == 82

    def test_bad_token_returns_403(self, client: TestClient, sample_job: Job):
        """Token sai → 403 Forbidden."""
        res = client.get(
            f"/jobs/{sample_job.id}/result",
            params={"access_token": "totally_wrong_token"},
        )
        assert res.status_code == 403
        assert "Invalid" in res.json()["detail"]

    def test_missing_token_returns_422(self, client: TestClient, sample_job: Job):
        """Không có token → 422 Unprocessable Entity (FastAPI validation)."""
        res = client.get(f"/jobs/{sample_job.id}/result")
        assert res.status_code == 422

    def test_empty_token_returns_403(self, client: TestClient, sample_job: Job):
        """Token rỗng → 403."""
        res = client.get(
            f"/jobs/{sample_job.id}/result",
            params={"access_token": ""},
        )
        assert res.status_code == 403

    def test_bad_job_id_returns_404(self, client: TestClient):
        """Job id không tồn tại → 404."""
        fake_id = str(uuid.uuid4())
        res = client.get(
            f"/jobs/{fake_id}/result",
            params={"access_token": "any_token"},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_token_from_different_job_returns_403(
        self, client: TestClient, sample_job: Job, pending_job: Job
    ):
        """Token của job khác → 403 (token không dùng chéo được)."""
        res = client.get(
            f"/jobs/{sample_job.id}/result",
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 403

    def test_pending_job_result_is_none(self, client: TestClient, pending_job: Job):
        """Job pending → result là null nhưng không lỗi."""
        res = client.get(
            f"/jobs/{pending_job.id}/result",
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pending"
        assert data["result"] is None

    def test_failed_job_returns_error_message(
        self, client: TestClient, failed_job: Job
    ):
        """Job failed → trả về error_message."""
        res = client.get(
            f"/jobs/{failed_job.id}/result",
            params={"access_token": failed_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None
        assert "timeout" in data["error_message"].lower()


class TestAccessTokenReport:
    """Tests cho GET /jobs/{job_id}/report với access token."""

    def test_valid_token_done_job_returns_report_info(
        self, client: TestClient, sample_job: Job
    ):
        """Token đúng, job done → thông tin report."""
        res = client.get(
            f"/jobs/{sample_job.id}/report",
            params={"access_token": sample_job.access_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert "report_s3_key" in data

    def test_bad_token_report_returns_403(self, client: TestClient, sample_job: Job):
        """Token sai cho report → 403."""
        res = client.get(
            f"/jobs/{sample_job.id}/report",
            params={"access_token": "wrong_token_here"},
        )
        assert res.status_code == 403

    def test_missing_token_report_returns_422(
        self, client: TestClient, sample_job: Job
    ):
        """Không có token cho report → 422."""
        res = client.get(f"/jobs/{sample_job.id}/report")
        assert res.status_code == 422

    def test_pending_job_report_returns_409(
        self, client: TestClient, pending_job: Job
    ):
        """Job chưa xong → 409 Conflict (report not ready)."""
        res = client.get(
            f"/jobs/{pending_job.id}/report",
            params={"access_token": pending_job.access_token},
        )
        assert res.status_code == 409
        assert "not ready" in res.json()["detail"].lower()

    def test_bad_job_id_report_returns_404(self, client: TestClient):
        """Job id không tồn tại → 404."""
        res = client.get(
            f"/jobs/{uuid.uuid4()}/report",
            params={"access_token": "any"},
        )
        assert res.status_code == 404

    def test_missing_report_s3_key_returns_404(
        self, client: TestClient, db_session, sample_job: Job
    ):
        """Job done nhưng report chưa được tạo → 404."""
        sample_job.report_s3_key = None
        db_session.commit()

        res = client.get(
            f"/jobs/{sample_job.id}/report",
            params={"access_token": sample_job.access_token},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


class TestJobStatus:
    """Tests cho GET /jobs/{job_id} — không cần token."""

    def test_get_status_no_token_needed(self, client: TestClient, sample_job: Job):
        """Status endpoint không cần token."""
        res = client.get(f"/jobs/{sample_job.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == sample_job.id
        assert data["status"] == "done"

    def test_get_status_bad_id_returns_404(self, client: TestClient):
        """Status với job id sai → 404."""
        res = client.get(f"/jobs/{uuid.uuid4()}")
        assert res.status_code == 404
