# Alembic Migration — Hướng dẫn sử dụng

## Tổng quan

Alembic là tool quản lý schema của database, tương tự như Git cho code.
Mỗi thay đổi schema (thêm bảng, thêm cột, đổi kiểu dữ liệu) phải được ghi
lại thành một **migration file** trong `alembic/versions/`.

---

## Setup lần đầu (chỉ làm một lần)

```bash
cd backend
pip install alembic psycopg2-binary
```

Cấu trúc thư mục sau khi setup:
```
backend/
├── alembic/
│   ├── env.py              ← cấu hình kết nối DB và metadata
│   └── versions/
│       └── 0001_baseline.py  ← migration đầu tiên
├── alembic.ini             ← config file
└── app/
    └── models/
        └── job.py          ← SQLAlchemy models
```

---

## Chạy migration

### Lên version mới nhất (thường dùng nhất)

```bash
cd backend
export DATABASE_URL=postgresql://user:password@localhost:5432/ai_cv_fit
alembic upgrade head
```

### Xem trạng thái hiện tại

```bash
alembic current
```

### Xem lịch sử tất cả migrations

```bash
alembic history --verbose
```

---

## Tạo migration mới khi thay đổi models

### Cách 1: Autogenerate (khuyến nghị)

Sau khi sửa model trong `app/models/`, chạy:

```bash
alembic revision --autogenerate -m "add_column_xyz_to_jobs"
```

Alembic tự so sánh model với DB hiện tại và sinh ra file migration.

**⚠️ Quan trọng:** Luôn mở file migration vừa tạo và kiểm tra trước khi chạy.
Autogenerate không phải lúc nào cũng đúng 100%.

### Cách 2: Tạo file rỗng và tự viết

```bash
alembic revision -m "add_index_on_created_at"
```

Sau đó tự viết hàm `upgrade()` và `downgrade()` trong file được tạo.

---

## Rollback migration

### Về 1 version trước

```bash
alembic downgrade -1
```

### Về một version cụ thể

```bash
alembic downgrade 0001_baseline
```

### Về trạng thái ban đầu (xóa hết)

```bash
alembic downgrade base
```

---

## Quy trình khi làm việc nhóm

1. **Pull code mới** → luôn chạy `alembic upgrade head` để apply migration của người khác
2. **Sửa model** → chạy `alembic revision --autogenerate -m "mô tả thay đổi"`
3. **Kiểm tra file migration** được tạo ra
4. **Chạy** `alembic upgrade head` để test migration trên local
5. **Commit cả 2**: file model đã sửa + file migration mới

---

## Trên Render (production)

Render không tự chạy migration. Có 2 cách:

### Cách 1: Thêm vào start command của Web Service

Trong Render dashboard → Web Service → Settings → Start Command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Cách 2: Chạy thủ công qua Render Shell

```bash
# Vào Render dashboard → Web Service → Shell
alembic upgrade head
```

---

## Troubleshooting

### Lỗi "Target database is not up to date"

```bash
alembic upgrade head
```

### Lỗi "Can't locate revision"

File migration trong `alembic/versions/` không match với DB.
Kiểm tra bằng: `alembic history` và `alembic current`.

### Lỗi sau khi merge branch

Nếu 2 người cùng tạo migration từ cùng một revision:
1. Chỉnh `down_revision` của file mới hơn để trỏ vào file kia
2. Hoặc dùng `alembic merge` để gộp 2 heads:

```bash
alembic merge -m "merge heads" <revision_1> <revision_2>
```

### Reset hoàn toàn (chỉ dùng cho dev)

```bash
# Xóa tất cả bảng và chạy lại từ đầu
alembic downgrade base
alembic upgrade head
```
