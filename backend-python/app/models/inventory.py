"""库存域模型 — 对标领星WMS

- Batch        批次：一次入库收货生成一个批次，支持有效期管理（简化版）
- Inventory    库存行：product + location + batch 维度，可用量(available) 与 锁定量(locked) 分离
               （locked 对应领星的"拣货暂存/锁定库存"）
- InventoryFlow 库存流水：每一次库存变动必须写流水（单据类型+单号+库位+批次+变动前后），全量可追溯
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Batch(Base):
    """库存批次"""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(50), nullable=False, unique=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    inbound_date = Column(DateTime, nullable=False)      # 入库上架日期
    manufacture_date = Column(DateTime, nullable=True)   # 生产日期（可选）
    expiry_date = Column(DateTime, nullable=True)        # 有效期（可选）
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product")


class Inventory(Base):
    """库存行（可用量 + 锁定量）

    唯一约束 (product_id, location_code, batch_id)：
    同商品同库位可按不同批次分行管理。
    """
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "location_code", "batch_id",
            name="uk_product_location_batch",
        ),
        # 库存查询常用过滤列建索引，避免全表扫描
        Index("ix_inventory_location_code", "location_code"),
        Index("ix_inventory_product_id", "product_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_code = Column(String(50), ForeignKey("locations.code"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    available_qty = Column(Integer, nullable=False, default=0)  # 可用库存
    locked_qty = Column(Integer, nullable=False, default=0)     # 锁定库存（拣货暂存）
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("Product")
    location = relationship("Location")
    batch = relationship("Batch")


class InventoryFlow(Base):
    """库存流水 — 全量可追溯

    flow_type：
      INBOUND       入库收货（+）
      OUTBOUND      出库发货（-）
      PICK_LOCK     拣货锁定（available- / locked+）
      PICK_UNLOCK   拣货取消（反向）
      MOVE_OUT      移库出（-）
      MOVE_IN       移库入（+）
      ADJUST_IN     库存调整增加（+）
      ADJUST_OUT    库存调整减少（-）
    """
    __tablename__ = "inventory_flows"
    __table_args__ = (
        Index("ix_flows_order_no", "order_no"),
        Index("ix_flows_product_id", "product_id"),
        Index("ix_flows_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_type = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)  # INBOUND/OUTBOUND/TRANSFER/ADJUSTMENT
    order_no = Column(String(50), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_code = Column(String(50), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    quantity = Column(Integer, nullable=False)        # 变动量（可为负）
    before_qty = Column(Integer, nullable=True)       # 变动前可用量
    after_qty = Column(Integer, nullable=True)        # 变动后可用量
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product")
    batch = relationship("Batch")
