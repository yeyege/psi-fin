"""基础数据模型 — 对标领星WMS

层级：仓库(Warehouse) → 库区(Zone, 正品区/残次品区) → 库位(Location, 带优先级)
商品(SKU)：含尺寸重量，用于后续计费/拣货推荐等场景。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """商品 SKU"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    unit = Column(String(20), default="个")
    # 尺寸重量（cm / kg），领星用于计费与装箱
    width = Column(Float, default=0)
    height = Column(Float, default=0)
    length = Column(Float, default=0)
    weight = Column(Float, default=0)
    status = Column(String(20), default="ACTIVE")  # ACTIVE / INACTIVE
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Warehouse(Base):
    """仓库"""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.now)


class Zone(Base):
    """库区 — 正品区(GOODS) / 残次品区(DEFECT)"""
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(20), default="GOODS")  # GOODS 正品区 / DEFECT 残次品区
    created_at = Column(DateTime, default=datetime.now)

    warehouse = relationship("Warehouse")


class Location(Base):
    """库位 — 归属库区，priority 越大优先级越高（领星推荐上架位时使用）"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False, unique=True, index=True)
    priority = Column(Integer, default=0)
    status = Column(String(20), default="FREE")  # FREE / OCCUPIED
    created_at = Column(DateTime, default=datetime.now)

    zone = relationship("Zone")
    warehouse = relationship("Warehouse")
