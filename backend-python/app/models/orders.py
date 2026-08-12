"""单据域模型 — 对标领星WMS（状态机流转）

- InboundOrder    入库单：PENDING(待收货) → COMPLETED(已收货上架，库存生效)
- OutboundOrder   出库单：PENDING(待拣货) → PICKED(已拣货，库存锁定) → SHIPPED(已发货，扣减)
- ReturnOrder     退货单：PENDING(待收货) → RECEIVED(已收货登记) → DONE(处理完成)
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
    status = Column(String(20), default="PENDING")  # PENDING → PICKED → REVIEWED → SHIPPED
    wave_id = Column(Integer, ForeignKey("waves.id"), nullable=True)  # 归属波次
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship(
        "OutboundOrderItem", back_populates="order",
        cascade="all, delete-orphan",
    )
    wave = relationship("Wave", back_populates="outbound_orders")


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


class Wave(Base):
    """波次 — 聚合多张待拣货出库单，一键生成拣货单

    对标领星智能波次策略：按客户/状态等条件聚合出库单 → 生成拣货任务。
    状态机：CREATED(已生成) → PICKING(拣货中) → COMPLETED(全部拣货完成)
    """
    __tablename__ = "waves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wave_no = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), default="CREATED")  # CREATED → PICKING → COMPLETED
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    outbound_orders = relationship("OutboundOrder", back_populates="wave")
    picking_orders = relationship(
        "PickingOrder", back_populates="wave",
        cascade="all, delete-orphan",
    )


class PickingOrder(Base):
    """拣货单 — 一个出库单一张，明细按(商品,库位)聚合，按库位优先级排序

    状态机：CREATED(待拣货) → PICKED(已拣货，库存锁定)
    """
    __tablename__ = "picking_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    picking_no = Column(String(50), nullable=False, unique=True)
    wave_id = Column(Integer, ForeignKey("waves.id"), nullable=False)
    outbound_order_id = Column(Integer, ForeignKey("outbound_orders.id"), nullable=False)
    status = Column(String(20), default="CREATED")  # CREATED → PICKED
    created_at = Column(DateTime, default=datetime.now)

    wave = relationship("Wave", back_populates="picking_orders")
    outbound_order = relationship("OutboundOrder")
    items = relationship(
        "PickingOrderItem", back_populates="picking_order",
        cascade="all, delete-orphan",
    )


class PickingOrderItem(Base):
    """拣货单明细（商品×库位，quantity 聚合）"""
    __tablename__ = "picking_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    picking_order_id = Column(Integer, ForeignKey("picking_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    location_code = Column(String(50), nullable=False)

    picking_order = relationship("PickingOrder", back_populates="items")
    product = relationship("Product")


class ReturnOrder(Base):
    """退货单（FBA退货 / 买家退件 / 服务商退件）

    - source：FBA / SELLER / CARRIER
    - 状态机：PENDING(待收货) → RECEIVED(已收货登记) → DONE(处理完成)
    - 收货时按明细 disposition 处理：RESELL/RELABEL 转正品累加库存，SCRAP 报废不累加
    """
    __tablename__ = "return_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    source = Column(String(20), default="FBA")  # FBA / SELLER / CARRIER
    status = Column(String(20), default="PENDING")
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer")
    items = relationship(
        "ReturnOrderItem", back_populates="order",
        cascade="all, delete-orphan",
    )


class ReturnOrderItem(Base):
    """退货单明细

    disposition：
      RESELL  转正品（收货后累加库存）
      RELABEL 换标后转正品（收货后累加库存，语义标记换标需求）
      SCRAP   报废（收货登记但不累加库存）
    """
    __tablename__ = "return_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("return_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    location_code = Column(String(50), nullable=False)  # 目标库位（转正品时上架）
    disposition = Column(String(20), default="RESELL")
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)  # 收货后回填批次

    order = relationship("ReturnOrder", back_populates="items")
    product = relationship("Product")
    batch = relationship("Batch")


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
