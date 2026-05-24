"""
Alembic environment configuration.
Đọc DATABASE_URL từ env var, dùng model metadata để autogenerate migration.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Thêm backend vào sys.path để import được app models ──────────────────────
# Tính từ vị trí của env.py (alembic/env.py)
_alembic_dir = Path(__file__).parent
_backend_dir = _alembic_dir.parent  # backend/ nằm cùng cấp với alembic/

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.models import Base  # noqa: E402  import sau khi fix path

# ─── Alembic Config ──────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url từ environment variable
# (Không hardcode URL vào alembic.ini)
database_url = os.environ.get("DATABASE_URL", "")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Logging config từ alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata của tất cả models — dùng cho autogenerate
target_metadata = Base.metadata


# ─── Migration functions ─────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Chạy migration trong 'offline' mode (không cần kết nối DB).
    Xuất ra SQL script thay vì chạy trực tiếp.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Chạy migration trong 'online' mode (kết nối DB trực tiếp).
    Dùng cho môi trường dev/staging/prod thông thường.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,       # detect column type changes
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
