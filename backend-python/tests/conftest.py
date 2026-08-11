"""pytest 公共夹具

使用独立的临时 SQLite 数据库，与开发库 wms.db 隔离，测试互不影响。
"""
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Product, Warehouse, Location


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
    # 基础数据：1 商品 + 1 仓库 + 2 库位
    session.add_all([
        Product(id=1, name="测试商品A", sku="T-001", unit="个"),
        Product(id=2, name="测试商品B", sku="T-002", unit="个"),
        Warehouse(id=1, code="WH-T", name="测试仓"),
        Location(id=1, warehouse_id=1, code="LOC-01", status="FREE"),
        Location(id=2, warehouse_id=1, code="LOC-02", status="FREE"),
    ])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)
