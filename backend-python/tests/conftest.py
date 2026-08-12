"""pytest 公共夹具

使用独立的临时 SQLite 数据库，与开发库 wms.db 隔离，测试互不影响。
基础数据：2 商品 + 1 仓库 + 1 库区 + 2 库位（新模型：Location 归属 Zone）。
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Product, Customer, Warehouse, Zone, Location
from app.schemas import UserCreate
from app.services import auth_service


@pytest.fixture()
def db_session():
    """提供一个已建表、已注入基础数据的临时数据库会话。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    # 基础数据：2 商品 + 1 客户 + 1 仓库 + 1 正品库区 + 2 库位（带优先级）
    session.add_all([
        Product(id=1, name="测试商品A", sku="T-001", unit="个"),
        Product(id=2, name="测试商品B", sku="T-002", unit="个"),
        Customer(id=1, code="CUST-T", name="测试客户", tier="A"),
        Warehouse(id=1, code="WH-T", name="测试仓"),
        Zone(id=1, warehouse_id=1, code="Z-GOODS", name="正品区", zone_type="GOODS"),
        Location(id=1, zone_id=1, warehouse_id=1, code="LOC-01", priority=5),
        Location(id=2, zone_id=1, warehouse_id=1, code="LOC-02", priority=4),
    ])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture()
def client():
    """TestClient + 独立临时库（dependency_overrides 隔离，不触碰开发库）。

    自带 admin/admin123 账号，供 API 层测试登录鉴权后使用。
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
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
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
