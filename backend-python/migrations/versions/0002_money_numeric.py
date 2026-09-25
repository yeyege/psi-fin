"""money_numeric: 7 个金额列 FLOAT → NUMERIC(18,2)

对应 AGENTS.md §4「金额一律 Numeric(18,2) + Decimal，禁止浮点」。迁移前这些列是
FLOAT，服务层用 round(...,2) 与 EPS=1e-6 容差兜浮点残差；模型侧已改为
models.base.Money = Numeric(18,2)，本迁移把存量库的列类型真正改过来。

要点：
- create_all 不会 ALTER 已存在的表，所以这条迁移不可省；只改代码不迁库等于
  只有新建库和测试库是 Numeric，线上列类型仍是 FLOAT。
- 走 batch_alter_table：SQLite 不支持 ALTER COLUMN（env.py 对 SQLite 开
  render_as_batch），MySQL/PostgreSQL 下批量模式退化为直接 ALTER，
  一份脚本覆盖三种方言。
- PostgreSQL 显式 USING ::numeric(18,2)，MySQL 隐式 MODIFY，均四舍五入到 2 位；
  与 app.common.money 的 ROUND_HALF_UP 口径一致，存量值最多差 1 分（见计划的风险条目）。
- SQLite 是个例外：批量重建只是原样搬行，REAL → NUMERIC 并不截到 2 位，
  浮点残差（实测 0.30000000000000004）会原封不动躺在库里。ORM 读出来会按
  return_scale 量化，所以接口上看不出来，但对账 SQL 会看到脏值。
  因此 ALTER 之后再补一步 ROUND(col, 2) 归一：三种方言都有 ROUND(x, 2)，
  对已经截好的 PG/MySQL 值是幂等操作。

Revision ID: 0002_money_numeric
Revises: 0001_baseline
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_money_numeric"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(18, 2)
FLOAT = sa.Float()

# (表名, 列名) — 与 models/finance.py、models/accounting.py 的金额列一一对应
MONEY_COLUMNS = [
    ("sales_orders", "total_amount"),
    ("sales_order_items", "unit_price"),
    ("sales_order_items", "amount"),
    ("finance_entries", "amount"),
    ("finance_entries", "settled_amount"),
    ("finance_settlements", "amount"),
    ("voucher_lines", "amount"),
]


def _to_numeric(table: str, column: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.alter_column(
            column,
            existing_type=FLOAT,
            type_=MONEY,
            existing_nullable=False,
            postgresql_using=f"{column}::numeric(18,2)",
        )
    # 存量值归一到分：SQLite 的 cast 不截位，PG/MySQL 上这步幂等
    op.execute(sa.text(f"UPDATE {table} SET {column} = ROUND({column}, 2)"))


def _to_float(table: str, column: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.alter_column(
            column,
            existing_type=MONEY,
            type_=FLOAT,
            existing_nullable=False,
            postgresql_using=f"{column}::double precision",
        )


def upgrade() -> None:
    for table, column in MONEY_COLUMNS:
        _to_numeric(table, column)


def downgrade() -> None:
    for table, column in reversed(MONEY_COLUMNS):
        _to_float(table, column)
