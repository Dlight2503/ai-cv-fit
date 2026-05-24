# AI CV Fit - Phase 1 MVP

API Backend cho ứng dụng phân tích CV và chấm điểm mức độ phù hợp với Job Description.

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-cv-fit.git
cd ai-cv-fit
```

### 2. Tạo Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt Dependencies

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Dev dependencies (testing)
cd ..
pip install -r requirements-dev.txt
```

### 4. Chạy Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Server sẽ chạy tại: **http://127.0.0.1:8000**

### 5. Truy cập API

| URL | Mô tả |
|-----|--------|
| http://127.0.0.1:8000/docs | Swagger UI (API Documentation) |
| http://127.0.0.1:8000/health | Health check |

## API Endpoints

### Tạo Job mới

```bash
POST /jobs/

Body:
{
  "jd_text": "Backend Python engineer với 3 năm kinh nghiệm"
}

Response:
{
  "job_id": "abc-123...",
  "access_token": "xyz-456...",
  "status": "pending"
}
```

### Upload CV

```bash
POST /upload/cv/{job_id}?access_token={token}

Form Data:
- file: resume.pdf hoặc resume.docx
```

### Xem Kết quả

```bash
GET /jobs/{job_id}/result?access_token={token}
```

### Tải Report

```bash
GET /jobs/{job_id}/report?access_token={token}
```

## Chạy Tests

```bash
# Tất cả tests
python -m pytest tests/ -v

# Test cụ thể
python -m pytest tests/test_access_token.py -v
```

**Kết quả:** 31 tests phải pass hết.

## Project Structure

```
ai-cv-fit/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── core/
│   │   │   └── database.py  # DB connection
│   │   ├── models/
│   │   │   └── job.py       # Job model + access token
│   │   └── routers/
│   │       ├── jobs.py      # Job endpoints
│   │       └── upload.py     # Upload endpoint
│   └── requirements.txt
├── alembic/                  # Database migrations
│   ├── env.py
│   └── versions/
│       └── 0001_baseline.py
├── tests/                    # Test suite
│   ├── conftest.py
│   ├── test_access_token.py
│   ├── test_jobs.py
│   └── test_upload.py
└── docs/                     # Documentation
    ├── alembic_migration_guide.md
    └── s3_cleanup_checklist.md
```

## Database Migrations

```bash
# Chạy migrations
cd backend
alembic upgrade head

# Tạo migration mới
alembic revision --autogenerate -m "describe change"

# Rollback
alembic downgrade -1
```

## Environment Variables (Optional)

| Variable | Mô tả | Default |
|----------|--------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite local |
| `REDIS_URL` | Redis URL cho Celery | - |
| `STORAGE_BACKEND` | `local` hoặc `s3` | `local` |

## Team Members

- **Phúc** - Backend / Deployment Lead
- **Quân** - Frontend / UI Owner
- **Đạt** - Backend Quality / Testing

## License

MIT
