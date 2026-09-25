"""Alembic 运行环境 — 持久库结构变更的唯一入口

约定（见 AGENTS.md §4）：
- 连接串只从 DATABASE_URL 读，缺失即报错退出。绝不静默回退本地 SQLite，
  否则会出现「以为迁了线上，其实只动了本地文件」这种没有证据的迁移。
- SQLite 走 render_as_batch=True：它不支持 ALTER COLUMN，批量模式会自动重建表，
  因此同一份迁移脚本在 SQLite / MySQL 8.0 / PostgreSQL 上都能跑。
- 迁移脚本只写 sa.* 原生类型，不 import app.models 的列别名（Money），
  避免模型改名把历史迁移一起打断。
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 让 `alembic` 命令在任何 CWD 下都能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base  # noqa: E402
from app import models  # noqa: E402,F401 — 导入即把全部表注册进 Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if not database_url:
    sys.exit(
        "DATABASE_URL 未设置：迁移必须显式指向目标库（本地 compose 的 MySQL 或线上 PostgreSQL），"
        "禁止静默回退本地 SQLite。"
    )
# configparser 会把 % 当插值语法，连接串里的编码字符要转义
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
