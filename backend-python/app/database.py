import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# 数据库连接策略：
# - 默认 SQLite（本地开发零配置，wms.db）
# - 设置 DATABASE_URL 环境变量可无缝切换 MySQL/PostgreSQL
#   例如 Docker 编排：mysql+pymysql://wms:wms@mysql:3306/wms?charset=utf8mb4
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    connect_args = {}
else:
    # 使用相对于本文件的路径，避免 CWD 问题
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wms.db")
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
