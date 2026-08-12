"""单据域模型 — 对标领星WMS（状态机流转）

- InboundOrder    入库单：PENDING(待收货) → COMPLETED(已收货上架，库存生效)
- OutboundOrder   出库单：PENDING(待拣货) → PICKED(已拣货，库存锁定) → SHIPPED(已发货，扣减)
- StockTransfer   移库单：直接完成（库位间转移，双向流水）
- StockAdjustment 库存调整：直接完成（盘盈盘亏，流水）
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class InboundOrder(Base):
    """入库单主表"""
    __tablename__ = "inbound_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    supplier_name = Column(String(200))
    status = Column(String(20), default="PENDING")  # PENDING → COMPLETED
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship(
        "InboundOrderItem", back_populates="order",
        cascade="all, delete-orphan",
    )


class InboundOrderItem(Base):
    """入库单明细"""
    __tablename__ = "inbound_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("inbound_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    location_code = Column(String(50), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)  # 收货后回填批次

    order = relationship("InboundOrder", back_populates="items")
    product = relationship("Product")
    batch = relationship("Batch")


class OutboundOrder(Base):
    """出库单主表"""
    __tablename__ = "outbound_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_name = Column(String(200))
    status = Column(String(20), default="PENDING")  # PENDING → PICKED → SHIPPED
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship(
        "OutboundOrderItem", back_populates="order",
        cascade="all, delete-orphan",
    )


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


class StockTransfer(Base):
    """移库单（库位间转移）"""
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="COMPLETED")
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship(
        "StockTransferItem", back_populates="transfer",
        cascade="all, delete-orphan",
    )


class StockTransferItem(Base):
    """移库明细：from_location → to_location"""
    __tablename__ = "stock_transfer_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    from_location_code = Column(String(50), nullable=False)
    to_location_code = Column(String(50), nullable=False)

    transfer = relationship("StockTransfer", back_populates="items")
    product = relationship("Product")


class StockAdjustment(Base):
    """库存调整单（盘盈盘亏）"""
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="COMPLETED")
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship(
        "StockAdjustmentItem", back_populates="adjustment",
        cascade="all, delete-orphan",
    )


class StockAdjustmentItem(Base):
    """调整明细：change_qty 为正表示盘盈（+），负表示盘亏（-）"""
    __tablename__ = "stock_adjustment_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    adjustment_id = Column(Integer, ForeignKey("stock_adjustments.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_code = Column(String(50), nullable=False)
    change_qty = Column(Integer, nullable=False)

    adjustment = relationship("StockAdjustment", back_populates="items")
    product = relationship("Product")
