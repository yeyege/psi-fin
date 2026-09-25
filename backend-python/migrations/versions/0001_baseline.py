"""baseline: 按当前 ORM 模型建全量表

项目此前没有迁移工具链，结构靠 app/main.py 启动时的 Base.metadata.create_all。
本迁移把「已有库」与「全新库」统一到同一条版本线上：

- 全新库：create_all 建出全部表；
- 存量库（本地 MySQL / 线上 PostgreSQL）：create_all 只补缺失表，已存在的表原样跳过，
  所以这条迁移对存量库是 no-op，不需要 alembic stamp 即可直接 upgrade。

downgrade 会按模型的依赖倒序删表，只在「刚建的空库需要回退」时用，禁止对有线上数据的库执行。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-26
"""
from alembic import op

from app.database import Base
from app import models  # noqa: F401 — 导入即把全部表注册进 Base.metadata

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
