from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False, unique=True)
    unit = Column(String(20), default="个")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Warehouse(Base):
    """仓库"""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)


class Location(Base):
    """库位"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="FREE")

    warehouse = relationship("Warehouse")


class Inventory(Base):
    """库存 — 按商品 + 库位维度记录实时库存"""
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", "location_code", name="uk_product_location"),
        # 库存查询常用过滤条件：商品名/SKU 模糊搜索、仓库筛选、库位编码筛选
        # 这里给常用筛选列建索引，避免数据量增大后全表扫描
        Index("ix_inventory_location_code", "location_code"),
        Index("ix_inventory_product_id", "product_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_code = Column(String(50), ForeignKey("locations.code"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("Product", foreign_keys=[product_id])
    location = relationship("Location", foreign_keys=[location_code])


class InboundOrder(Base):
    """入库单主表"""
    __tablename__ = "inbound_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    supplier_name = Column(String(200))
    status = Column(String(20), default="DRAFT")
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("InboundOrderItem", back_populates="order", cascade="all, delete-orphan")


class InboundOrderItem(Base):
    """入库单明细"""
    __tablename__ = "inbound_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("inbound_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    location_code = Column(String(50), nullable=False)

    order = relationship("InboundOrder", back_populates="items")
    product = relationship("Product")


class OutboundOrder(Base):
    """出库单主表（选做 A）"""
    __tablename__ = "outbound_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_name = Column(String(200))
    status = Column(String(20), default="DRAFT")
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("OutboundOrderItem", back_populates="order", cascade="all, delete-orphan")


class OutboundOrderItem(Base):
    """出库单明细"""
    __tablename__ = "outbound_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("outbound_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    location_code = Column(String(50), nullable=False)

    order = relationship("OutboundOrder", back_populates="items")
    product = relationship("Product")
