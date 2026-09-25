"""迁移后的事实核对：7 个金额列在**真实数据库**里到底是不是 numeric(18,2)

只跑 `alembic upgrade head` 不报错不构成证据——列类型没变、或只改了模型没改库，
都会绿着过去。本脚本直接问数据库本身。

用法（DATABASE_URL 必填，缺省即报错，与 migrations/env.py 同一套纪律）：

    cd backend-python
    $env:DATABASE_URL="postgresql://..."; uv run python scripts/check_money_columns.py

CI 里在 postgres:16 上跑，见 .github/workflows/ci.yml 的 backend-migrate-postgres。
"""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# 本文件以 `python scripts/check_money_columns.py` 运行时，sys.path[0] 是 scripts/，
# 父目录不在路径上 —— 而下面要复用 app 的归一化函数，不能自己再抄一份 scheme 规则。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import normalize_database_url  # noqa: E402

# 与 app/models/finance.py、app/models/accounting.py 的金额列一一对应
MONEY_COLUMNS = [
    ("sales_orders", "total_amount"),
    ("sales_order_items", "unit_price"),
    ("sales_order_items", "amount"),
    ("finance_entries", "amount"),
    ("finance_entries", "settled_amount"),
    ("finance_settlements", "amount"),
    ("voucher_lines", "amount"),
]


def check_postgres_or_mysql(conn, dialect: str) -> list[str]:
    # 当前库的过滤表达式，两种方言不一样：PG 用 current_schema()，MySQL 用 DATABASE()
    schema_clause = (
        "table_schema = current_schema()" if dialect.startswith("postgres")
        else "table_schema = DATABASE()"
    )
    sql = text(
        f"SELECT data_type, numeric_precision, numeric_scale "
        f"FROM information_schema.columns "
        f"WHERE {schema_clause} "
        "AND lower(table_name) = lower(:t) AND lower(column_name) = lower(:c)"
    )
    bad = []
    for table, column in MONEY_COLUMNS:
        row = conn.execute(sql, {"t": table, "c": column}).first()
        if row is None:
            bad.append(f"{table}.{column}: 列不存在")
            continue
        data_type, precision, scale = row
        # MySQL 把 DECIMAL/NUMERIC 统一报成 decimal
        if data_type not in ("numeric", "decimal"):
            bad.append(f"{table}.{column}: data_type={data_type}（应为 numeric/decimal）")
        elif (precision, scale) != (18, 2):
            bad.append(f"{table}.{column}: 精度={precision} 小数位={scale}（应为 18,2）")
        else:
            print(f"OK   {table}.{column} -> {data_type}({precision},{scale})")
    return bad


def check_sqlite(conn) -> list[str]:
    bad = []
    for table in dict.fromkeys(t for t, _ in MONEY_COLUMNS):
        declared = {r[1]: (r[2] or "") for r in conn.execute(text(f"PRAGMA table_info({table})"))}
        for t, column in MONEY_COLUMNS:
            if t != table:
                continue
            kind = declared.get(column, "")
            if "NUMERIC(18, 2)" not in kind.upper().replace("NUMERIC(18,2)", "NUMERIC(18, 2)"):
                bad.append(f"{table}.{column}: 声明类型 {kind!r}（应为 NUMERIC(18, 2)）")
            else:
                print(f"OK   {table}.{column} -> {kind}")
    return bad


def main() -> int:
    # 必须过 normalize_database_url：裸 postgresql:// 在 SQLAlchemy 2.1 上会直接
    # ModuleNotFoundError（CI 的 Assert 步骤踩过），与 app 与 alembic 共用同一个归一化入口。
    url = normalize_database_url(os.getenv("DATABASE_URL"))
    if not url:
        print("DATABASE_URL 未设置：拒绝在未知的库上给出「迁移已生效」的结论。")
        return 2
    engine = create_engine(url)
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "sqlite":
            bad = check_sqlite(conn)
        elif dialect in ("postgresql", "mysql", "mariadb"):
            bad = check_postgres_or_mysql(conn, dialect)
        else:
            print(f"未支持的方言: {dialect}")
            return 2
    engine.dispose()
    if bad:
        print("\n".join(f"FAIL {line}" for line in bad))
        return 1
    print(f"\n全部 7 个金额列在 {dialect} 上确为 2 位小数定点类型。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
