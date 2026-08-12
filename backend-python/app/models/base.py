"""基础数据模型 — 对标领星WMS

层级：仓库(Warehouse) → 库区(Zone, 正品区/残次品区) → 库位(Location, 带优先级)
商品(SKU)：含尺寸重量，用于后续计费/拣货推荐等场景。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """商品 SKU

    - fns_ku：FBA 仓库使用的 FNSKU（Amazon 场景标识，退货换标等场景按 FNSKU 精准管理）
    - case_qty：每箱数量（箱规），为后续「产品-箱-批次-库位」四维库存预留
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    fns_ku = Column(String(50), nullable=True, index=True)  # FNSKU（FBA 库内标识）
    case_qty = Column(Integer, default=1)  # 每箱数量（箱规）
    unit = Column(String(20), default="个")
    # 尺寸重量（cm / kg），领星用于计费与装箱
    width = Column(Float, default=0)
    height = Column(Float, default=0)
    length = Column(Float, default=0)
    weight = Column(Float, default=0)
    status = Column(String(20), default="ACTIVE")  # ACTIVE / INACTIVE
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Customer(Base):
    """客户 — 分层管理（A/B/C），出库单/退货单归属客户

    对标领星：客户分层用于运营策略与计费差异化管理。
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    tier = Column(String(10), default="C")  # A / B / C 客户分层
    contact = Column(String(50), nullable=True)   # 联系人
    phone = Column(String(50), nullable=True)     # 联系电话
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
