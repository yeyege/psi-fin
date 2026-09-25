"""DATABASE_URL 归一化测试 — 平台注入的裸 postgresql:// 必须钉住 psycopg2

seam：`app.database.normalize_database_url()`，即「平台连接串进入本应用」的那道边界。

为什么要有这条测试：SQLAlchemy 2.1 起，裸 `postgresql://` 只解析 psycopg(3)，
不再在缺失时自动回退 psycopg2。本项目的 PG 驱动是 `psycopg2-binary`，而 Render / Neon /
Vercel 注入的都是裸 scheme —— 于是「本地 uv.lock 钉在 2.0.x 一切正常、CI 与线上装到 2.1
直接 ModuleNotFoundError」这种没有共同原因的分裂。2026-09-26 CI 的
`Backend alembic on PostgreSQL` job 就是被这个打挂的。
"""
import pytest
from sqlalchemy.engine.url import make_url

from app.database import normalize_database_url

CASES = [
    # (输入, 期望的 drivername)
    ("postgresql://u:p@ep-x.aws.neon.tech:5432/psi_fin?sslmode=require", "postgresql+psycopg2"),
    ("postgres://u:p@localhost:5432/psi_fin", "postgresql+psycopg2"),
    # 已显式声明驱动的，不得改写
    ("postgresql+psycopg2://u:p@localhost:5432/psi_fin", "postgresql+psycopg2"),
    ("postgresql+asyncpg://u:p@localhost:5432/psi_fin", "postgresql+asyncpg"),
    # 其他方言原样通过
    ("mysql+pymysql://u:p@mysql:3306/psi_fin?charset=utf8mb4", "mysql+pymysql"),
    ("sqlite:///./psi_fin.db", "sqlite"),
]


@pytest.mark.parametrize("raw,expected", CASES)
def test_normalize_keeps_driver_explicit(raw, expected):
    assert make_url(normalize_database_url(raw)).drivername == expected


def test_normalized_postgresql_url_builds_engine_without_psycopg3():
    """归一化后的串必须能在只装 psycopg2 的环境里建出引擎（构造期即解析驱动，不需要连库）。"""
    from sqlalchemy import create_engine

    url = normalize_database_url("postgresql://u:p@127.0.0.1:1/db")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg2"


def test_none_and_empty_are_passed_through():
    """空值必须原样返回，交给调用方回退本地 SQLite —— 不能在这里替平台猜库。"""
    assert normalize_database_url(None) is None
    assert normalize_database_url("") == ""


# 注：曾有过一条「裸 postgresql:// 不解析到 psycopg2」的反证用例，已删。
# 它在 SQLAlchemy 2.0.49（本地）与 2.1.1（CI）上结果必然不同 —— 测的是上游版本行为而不是
# 本函数的契约，且与上面的参数化用例完全重叠。本函数的价值在于：不依赖上游回退是否存在。
