# AI CV Fit - Backend Quality / Testing

## Phần của Đạt - Backend Quality / Testing Owner

Repository này chứa phần backend quality và testing của AI CV Fit Phase 1.

---

## Mục lục

1. [Giới thiệu](#giới-thiệu)
2. [Cấu trúc project](#cấu-trúc-project)
3. [Access Token MVP](#access-token-mvp)
4. [Database Migrations](#database-migrations)
5. [Test Suite](#test-suite)
6. [S3 Cleanup](#s3-cleanup)
7. [Cách chạy](#cách-chạy)

---

## Giới thiệu

Phase 1 tập trung vào 4 phần chính:

| # | Deliverable | Mô tả |
|---|-------------|--------|
| 1 | Access Token MVP | Bảo mật result/report bằng token |
| 2 | Alembic Migration | Database migration baseline |
| 3 | Test Suite | 31 tests cover các edge cases |
| 4 | S3 Cleanup Checklist | Documentation cho việc dọn dẹp S3 |

---

## Cấu trúc project

```
ai-cv-fit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/
│   │   │   └── database.py      # DB connection (SQLite/PostgreSQL)
│   │   ├── models/
│   │   │   └── job.py           # Job model + access_token field
│   │   └── routers/
│   │       ├── jobs.py          # /jobs endpoints
│   │       └── upload.py        # /upload endpoints
│   └── requirements.txt
│
├── alembic/                      # Database migrations
│   ├── env.py
│   └── versions/
│       └── 0001_baseline.py     # Migration đầu tiên
│
├── tests/                        # Test suite
│   ├── conftest.py              # Fixtures (db, client, sample jobs)
│   ├── test_access_token.py     # 16 tests cho token validation
│   ├── test_jobs.py             # 7 tests cho job creation
│   └── test_upload.py           # 8 tests cho upload + worker
│
└── docs/
    ├── alembic_migration_guide.md
    └── s3_cleanup_checklist.md
```

---

## Access Token MVP

### Mục tiêu

Không ai có thể xem result/report chỉ bằng `job_id`. Cần có `access_token` hợp lệ.

### Cách hoạt động

1. **Tạo job** → nhận về `job_id` + `access_token`
2. **Frontend lưu** `access_token` (localStorage/session)
3. **Gọi /result hoặc /report** → kèm theo `access_token`

### Code mẫu

**Tạo job:**
```bash
POST /jobs/
{
  "jd_text": "Backend Python engineer"
}

Response:
{
  "job_id": "abc-123-def-456",
  "access_token": "xYz789...",
  "status": "pending"
}
```

**Xem kết quả (cần token):**
```bash
GET /jobs/{job_id}/result?access_token={token}
```

**Tải report (cần token):**
```bash
GET /jobs/{job_id}/report?access_token={token}
```

### Token validation logic

```python
# backend/app/models/job.py
def is_accessible_with_token(self, token: str) -> bool:
    """So sánh token an toàn, tránh timing attack."""
    return secrets.compare_digest(self.access_token, token)
```

### Security features

- Token dài 64 ký tự, random
- Dùng `secrets.compare_digest()` tránh timing attacks
- Token unique cho mỗi job

---

## Database Migrations

### Alembic setup

```bash
# Di chuyển vào backend
cd backend

# Chạy migrations
alembic upgrade head

# Tạo migration mới
alembic revision --autogenerate -m "add new column"

# Rollback
alembic downgrade -1

# Xem lịch sử
alembic history
```

### Migration hiện tại

**0001_baseline.py** tạo bảng `jobs` với các columns:

| Column | Type | Mô tả |
|--------|------|--------|
| `id` | String(36) | Primary key (UUID) |
| `access_token` | String(64) | Token bảo mật |
| `status` | String(20) | pending/processing/done/failed |
| `cv_s3_key` | String(512) | S3 path của CV |
| `jd_text` | Text | Job description |
| `result_json` | JSON | Kết quả phân tích |
| `report_s3_key` | String(512) | S3 path của report |
| `error_message` | Text | Lỗi nếu có |
| `created_at` | DateTime | Thời gian tạo |
| `updated_at` | DateTime | Thời gian cập nhật |

### Hỗ trợ SQLite và PostgreSQL

- **Development:** SQLite (tự động tạo `ai_cv_fit.db`)
- **Production:** PostgreSQL (set `DATABASE_URL`)

---

## Test Suite

### Chạy tests

```bash
# Tất cả tests
python -m pytest tests/ -v

# Test cụ thể
python -m pytest tests/test_access_token.py -v
python -m pytest tests/test_jobs.py -v
python -m pytest tests/test_upload.py -v

# Với coverage report
python -m pytest tests/ -v --cov=backend/app
```

### Kết quả

```
======================= 31 passed in 1.30s =======================
```

### Danh sách tests

#### test_access_token.py (16 tests)

| Test | Mô tả |
|------|--------|
| `test_valid_token_returns_result` | Token đúng → 200 |
| `test_bad_token_returns_403` | Token sai → 403 |
| `test_missing_token_returns_422` | Không có token → 422 |
| `test_empty_token_returns_403` | Token rỗng → 403 |
| `test_bad_job_id_returns_404` | Job ID không tồn tại → 404 |
| `test_token_from_different_job_returns_403` | Token job khác → 403 |
| `test_pending_job_result_is_none` | Job pending → result null |
| `test_failed_job_returns_error_message` | Job failed → có error |
| `test_valid_token_done_job_returns_report_info` | Report info |
| `test_bad_token_report_returns_403` | Report sai token → 403 |
| `test_missing_token_report_returns_422` | Report không token → 422 |
| `test_pending_job_report_returns_409` | Report chưa ready → 409 |
| `test_bad_job_id_report_returns_404` | Report job không tồn tại |
| `test_missing_report_s3_key_returns_404` | Report chưa tạo → 404 |
| `test_get_status_no_token_needed` | Status không cần token |
| `test_get_status_bad_id_returns_404` | Status job không tồn tại |

#### test_jobs.py (7 tests)

| Test | Mô tả |
|------|--------|
| `test_create_job_returns_201` | Tạo job → 201 |
| `test_create_job_returns_job_id_and_token` | Có job_id + token |
| `test_create_job_status_is_pending` | Status = pending |
| `test_create_job_tokens_are_unique` | Mỗi job token khác nhau |
| `test_create_job_missing_jd_text_returns_422` | Thiếu JD → 422 |
| `test_create_job_empty_jd_text` | JD rỗng (linh hoạt) |
| `test_token_usable_after_create` | Token dùng được ngay |

#### test_upload.py (8 tests)

| Test | Mô tả |
|------|--------|
| `test_upload_valid_pdf` | Upload PDF → 200 |
| `test_upload_invalid_file_type_returns_400` | File không hợp lệ → 400 |
| `test_upload_txt_file_rejected` | .txt bị từ chối → 400 |
| `test_upload_requires_valid_token` | Upload cần token |
| `test_upload_to_nonexistent_job_returns_404` | Job không tồn tại → 404 |
| `test_failed_job_has_error_message` | Failed job có error |
| `test_failed_job_result_is_none` | Failed job không có result |
| `test_failed_job_report_returns_409` | Failed job không có report |

### Fixtures có sẵn (conftest.py)

```python
@pytest.fixture
def sample_job(db_session):  # Job DONE với result

@pytest.fixture
def pending_job(db_session):  # Job PENDING mới

@pytest.fixture
def failed_job(db_session):  # Job FAILED với error

@pytest.fixture
def processing_job(db_session):  # Job PROCESSING
```

---

## S3 Cleanup

Xem chi tiết trong `docs/s3_cleanup_checklist.md`

### Tóm tắt

**Cấu trúc prefix:**
```
{S3_BUCKET}/
├── {S3_PREFIX}/cv/{job_id}/resume.pdf
└── {S3_PREFIX}/reports/{job_id}/report.docx
```

**Lifecycle policy khuyến nghị:**

| Environment | CV expire | Report expire |
|------------|-----------|---------------|
| dev | 7 ngày | 30 ngày |
| staging | 3 ngày | 14 ngày |
| prod | 90 ngày | 1 năm |

---

## Cách chạy

### 1. Clone về

```bash
git clone https://github.com/YOUR_USERNAME/ai-cv-fit.git
cd ai-cv-fit
```

### 2. Cài đặt môi trường

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# Cài dependencies
cd backend
pip install -r requirements.txt
cd ..

pip install -r requirements-dev.txt
```

### 3. Chạy server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Test API

Mở trình duyệt: **http://127.0.0.1:8000/docs**

Swagger UI cho phép test trực tiếp các endpoints.

### 5. Chạy tests

```bash
python -m pytest tests/ -v
```

---

## API Endpoints

| Method | Endpoint | Token | Mô tả |
|--------|----------|-------|--------|
| GET | `/health` | ❌ | Health check |
| POST | `/jobs/` | ❌ | Tạo job mới |
| GET | `/jobs/{id}` | ❌ | Xem status |
| GET | `/jobs/{id}/result` | ✅ | Xem kết quả |
| GET | `/jobs/{id}/report` | ✅ | Tải report |
| POST | `/upload/cv/{id}` | ✅ | Upload CV |

---

## Environment Variables

| Variable | Mô tả | Default |
|----------|--------|---------|
| `DATABASE_URL` | PostgreSQL connection | SQLite local |

---

## Files quan trọng

| File | Mô tả |
|------|--------|
| `backend/app/models/job.py` | Job model + access_token |
| `backend/app/routers/jobs.py` | Job endpoints |
| `backend/app/routers/upload.py` | Upload endpoint |
| `alembic/versions/0001_baseline.py` | DB migration |
| `tests/test_*.py` | 31 test cases |
| `docs/s3_cleanup_checklist.md` | S3 cleanup guide |

---

## Team

- **Phúc** - Backend / Deployment Lead
- **Quân** - Frontend / UI Owner
- **Đạt** - Backend Quality / Testing (phần này)
