"""pytest 公共夹具 — 跑在真实 PostgreSQL 上，不再跑 SQLite

为什么切（openspec `oss-finance-ai-platform` D12/D17，tasks 1.7b 的本地那一半）：
行级锁、`FOR UPDATE OF`、外键强制、varchar 长度、Numeric 精度在 SQLite 下没有真语义。
p0-2 组 2 是活教材 —— PostgreSQL 禁止对 LEFT JOIN 的可空侧加行锁，而 SQLite 静默忽略
FOR UPDATE，当时 145 个用例全绿也照不出这个错（AGENTS.md §4：以 SQLite 绿的测试为证据
等于没有证据）。

拿不到数据库时直接报错退出，不静默回退 SQLite —— 与 migrations/env.py 同一条原则。

隔离口径：每个用例前 `TRUNCATE ... RESTART IDENTITY CASCADE` 再注入基础数据。
`RESTART IDENTITY` 不是锦上添花：基础数据刻意不再显式写 `id=1`，因为 PostgreSQL 的序列
不会因显式插入 id 而前进，沿用 SQLite 那套写法会让服务层新建的第一条记录正好撞上主键冲突。
重置序列后每个用例拿到的主键与单号都一致，比 SQLite 时代更可复现。

用法：`docker compose up -d postgres`，然后 `uv run pytest`。
只设 DATABASE_URL 也行，夹具会把库名派生成 `<name>_test`。
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, normalize_database_url
from app.main import app
from app.models import Product, Customer, Warehouse, Zone, Location
from app.schemas import UserCreate
from app.services import auth_service

_START_HINT = "先 `docker compose up -d postgres`（compose 里的 postgres 服务，5432）"

# 允许据 DATABASE_URL 自动派生测试库的主机。容器内跟本地开发都算「本机」。
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "host.docker.internal")


def _test_database_url() -> str:
    """定位测试库连接串，两条来源的严格度不同。

    - **显式 `TEST_DATABASE_URL`**：照用，但仍要库名以 `_test` 结尾。
    - **只有 `DATABASE_URL`**：仅当主机是本机才允许把库名派生成 `<name>_test`。派生会原样
      继承主机、端口与凭据，若放任它指向远端，而远端恰好存在一个 `<name>_test` 库，
      夹具就会 TRUNCATE 它 —— `.env` 里把主机改成 Neon 只要一行，不是假想情形。
      本机之外一律要求显式设 `TEST_DATABASE_URL`。

    本夹具会 TRUNCATE 全部业务表，所以宁可报错退出，也不猜测。
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    raw = explicit or os.getenv("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "单测需要真实数据库，且不回退 SQLite（见本文件头注释与 AGENTS.md §4）。"
            f"{_START_HINT}，再设 "
            "TEST_DATABASE_URL=postgresql+psycopg2://psi_fin:psi_fin@localhost:5432/psi_fin_test"
            "（或只设本机 DATABASE_URL，夹具会自动把库名派生成 *_test）。"
        )
    url = make_url(normalize_database_url(raw))
    if not explicit:
        host = (url.host or "").lower()
        if host not in _LOCAL_HOSTS:
            raise RuntimeError(
                f"DATABASE_URL 指向非本机主机 {host!r}，拒绝据此派生测试库（TRUNCATE 跑在远端不可逆）。"
                "确需在本机之外跑单测，请显式设 TEST_DATABASE_URL（库名仍须以 _test 结尾）。"
            )
        db_name = url.database or ""
        if not db_name.endswith("_test"):
            url = url.set(database=f"{db_name}_test")
    if not (url.database or "").endswith("_test"):
        raise RuntimeError(f"拒绝在非 *_test 库上跑夹具（当前库名：{url.database!r}）")
    return url.render_as_string(hide_password=False)


# 夹具要 TRUNCATE 的表集合：取自模型元数据，新增表自动纳入，不维护第二份清单。
_ALL_TABLE_NAMES = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)


def _reset_data(engine) -> None:
    """清空全部业务表并把序列归零，等价于旧版「每个用例一个空 SQLite 文件」。"""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {_ALL_TABLE_NAMES} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def engine():
    """整个 pytest 会话共用一个引擎；表结构按模型重建一次。

    这里先 drop_all 是刻意的：create_all 只建缺失的表、不会 ALTER 已存在的列
    （AGENTS.md §4），测试库的结构必须每次等于模型。「持久库结构归 Alembic 管」这条
    纪律由 migrations/ + CI 的迁移轨负责，不在测试库里省这一步。

    并行会摧毁隔离：本夹具是「会话级建表 + 用例级 TRUNCATE」，多 worker 共用一个库
    会互相清掉对方正在用的数据，交出的是假绿而不是变慢，所以直接拒绝。
    真要并行需先改成每 worker 一个库名（按 worker id 派生），不是去掉这段守卫。
    """
    worker = os.getenv("PYTEST_XDIST_WORKER")
    if worker:
        raise RuntimeError(
            f"检测到 pytest-xdist（worker={worker}）：测试夹具不支持并行，"
            "参见本 fixture 的 docstring。请去掉 -n 参数。"
        )
    url = _test_database_url()
    eng = create_engine(url)
    try:
        with eng.begin() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise RuntimeError(
            f"连不上测试库（{url.split('@')[-1]}）：{_START_HINT}。原始错误：{exc}"
        ) from exc
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """提供一个已建表、已注入基础数据的会话。

    基础数据与旧版同构：2 商品 + 1 客户 + 1 仓库 + 1 正品库区 + 2 库位（带优先级），
    但改为逐条 flush 取 id —— 不写死主键，靠 RESTART IDENTITY 保证它们仍是 1,2,1,1,1,2。
    """
    _reset_data(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    for name, sku in (("测试商品A", "T-001"), ("测试商品B", "T-002")):
        product = Product(name=name, sku=sku, unit="个")
        session.add(product)
        session.flush()

    session.add(Customer(code="CUST-T", name="测试客户", tier="A"))
    session.flush()

    warehouse = Warehouse(code="WH-T", name="测试仓")
    session.add(warehouse)
    session.flush()

    zone = Zone(warehouse_id=warehouse.id, code="Z-GOODS", name="正品区", zone_type="GOODS")
    session.add(zone)
    session.flush()

    for code, priority in (("LOC-01", 5), ("LOC-02", 4)):
        session.add(Location(zone_id=zone.id, warehouse_id=warehouse.id,
                             code=code, priority=priority))
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    """TestClient + 测试库（dependency_overrides 隔离请求会话，不碰开发库）。

    与旧版一致：只建表并自带 admin/admin123 账号，不注入商品/库位基础数据。
    TestClient 不作为上下文管理器使用，因此不触发 lifespan —— 不会跑 create_all
    与 init_data 种子，测试库内容完全由本夹具决定。
    """
    _reset_data(engine)
    Session = sessionmaker(bind=engine)

    def _override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override

    s = Session()
    auth_service.create_user(
        s, UserCreate(username="admin", password="admin123", role="admin"))
    s.close()

    c = TestClient(app)
    yield c, Session

    app.dependency_overrides.clear()
