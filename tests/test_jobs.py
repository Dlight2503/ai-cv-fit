"""
Tests cho POST /jobs/ — tạo job mới.

Kiểm tra:
- Job được tạo đúng
- access_token được trả về
- Token đủ dài và random
"""

import pytest
from fastapi.testclient import TestClient


class TestCreateJob:
    def test_create_job_returns_201(self, client: TestClient):
        """Tạo job thành công → 201 Created."""
        res = client.post(
            "/jobs/",
            json={"jd_text": "Backend Python engineer với 3 năm kinh nghiệm"},
        )
        assert res.status_code == 201

    def test_create_job_returns_job_id_and_token(self, client: TestClient):
        """Response phải có job_id và access_token."""
        res = client.post(
            "/jobs/",
            json={"jd_text": "Frontend React developer"},
        )
        data = res.json()
        assert "job_id" in data
        assert "access_token" in data
        assert len(data["job_id"]) > 0
        assert len(data["access_token"]) >= 32  # token đủ dài

    def test_create_job_status_is_pending(self, client: TestClient):
        """Job mới tạo phải ở trạng thái pending."""
        res = client.post(
            "/jobs/",
            json={"jd_text": "Data scientist ML engineer"},
        )
        assert res.json()["status"] == "pending"

    def test_create_job_tokens_are_unique(self, client: TestClient):
        """Mỗi job phải có access_token khác nhau."""
        tokens = set()
        for _ in range(5):
            res = client.post("/jobs/", json={"jd_text": "Test JD"})
            tokens.add(res.json()["access_token"])
        assert len(tokens) == 5, "Tất cả token phải unique"

    def test_create_job_missing_jd_text_returns_422(self, client: TestClient):
        """Thiếu jd_text → 422 validation error."""
        res = client.post("/jobs/", json={})
        assert res.status_code == 422

    def test_create_job_empty_jd_text(self, client: TestClient):
        """jd_text rỗng — tùy business logic, hiện tại pass."""
        res = client.post("/jobs/", json={"jd_text": ""})
        # Tùy team quyết định có validate hay không
        # Hiện tại model chấp nhận để linh hoạt
        assert res.status_code in (201, 422)

    def test_token_usable_after_create(self, client: TestClient):
        """Token nhận từ create có thể dùng ngay để query result."""
        create_res = client.post(
            "/jobs/",
            json={"jd_text": "Backend engineer"},
        )
        job_id = create_res.json()["job_id"]
        token = create_res.json()["access_token"]

        result_res = client.get(
            f"/jobs/{job_id}/result",
            params={"access_token": token},
        )
        assert result_res.status_code == 200
        assert result_res.json()["status"] == "pending"
