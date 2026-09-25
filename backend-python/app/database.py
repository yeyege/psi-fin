import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# 本地开发：若存在 .env 则先加载（Render/Vercel 由平台注入环境变量，无 .env 时静默跳过）。
# 必须早于下方 os.getenv("DATABASE_URL")，否则 .env 中的配置读不到。
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv 未安装时不影响运行
    pass

# 数据库连接策略：
# - 默认 SQLite（本地开发零配置，psi_fin.db）
# - 设置 DATABASE_URL 环境变量可无缝切换 MySQL/PostgreSQL
#   例如 Docker 编排：mysql+pymysql://psi_fin:psi_fin@mysql:3306/psi_fin?charset=utf8mb4
# 生产环境可替换为 MySQL/PostgreSQL
# DATABASE_URL = "mysql+pymysql://user:pass@localhost:3306/psi_fin"


def normalize_database_url(raw: str | None) -> str | None:
    """把平台注入的裸 PG scheme 钉成显式驱动，空值原样返回（由调用方回退 SQLite）。

    必要原因：Render / Neon / Vercel 发的都是 `postgresql://` 或旧别名 `postgres://`，
    而本项目只装了 psycopg2-binary。SQLAlchemy 2.0 在 psycopg(3) 缺失时会隐式回退 psycopg2，
    **2.1 起这个回退没了**，裸串会在 `create_engine` 阶段直接 ModuleNotFoundError
    （依赖未锁版时，本地 uv.lock 在 2.0.x 一切正常、CI/线上装到 2.1 就挂）。
    已写明驱动的串（`postgresql+psycopg2://` / `+asyncpg://`）与其他方言一律不动。
    """
    if not raw:
        return raw
    for prefix in ("postgresql://", "postgres://"):
        if raw.startswith(prefix):
            return "postgresql+psycopg2://" + raw[len(prefix):]
    return raw


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    connect_args = {}
else:
    # 使用相对于本文件的路径，避免 CWD 问题
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "psi_fin.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    connect_args = {"check_same_thread": False}  # SQLite 需要

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
