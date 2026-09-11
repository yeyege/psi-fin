"""业财一体模型 — 销售订单 + 财务流水 + 核销

- SalesOrder        销售订单: DRAFT → CONFIRMED → SHIPPED → COMPLETED / CANCELLED
- SalesOrderItem    订单明细(数量 × 单价 = 金额)
- FinanceEntry      财务流水: 应收/应付/收款/付款,金额与已核销金额分离
- FinanceSettlement 核销明细: 一笔收款核销到某张应收(支持部分核销/预收)

设计要点(见 openspec/changes/add-business-finance/design.md):
- 金额字段用 Float(演示口径),服务层统一 round(...,2)
- finance_entries 对 (source_order_no, entry_type) 建唯一约束,作为应收生成的幂等兜底
- 收款流水的 amount 是到账金额、settled_amount 是已核销金额,差额即未核销余额(预收)
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Float, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ============ 销售订单 ============

class SalesOrder(Base):
    """销售订单主表"""
    __tablename__ = "sales_orders"
    __table_args__ = (
        Index("ix_sales_orders_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer_name = Column(String(200), nullable=False)  # 冗余:便于列表查询与业财核对
    status = Column(String(20), default="DRAFT", nullable=False)
    credit_days = Column(Integer, default=0, nullable=False)  # 账期(天):发货后用于算应收到期日
    total_amount = Column(Float, default=0, nullable=False)
    outbound_order_no = Column(String(50), nullable=True)  # 预留:关联出库单号(一期可为空)
    shipped_at = Column(DateTime, nullable=True)           # 发货时间
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    customer = relationship("Customer")
    items = relationship(
        "SalesOrderItem", back_populates="order",
        cascade="all, delete-orphan",
    )


class SalesOrderItem(Base):
    """销售订单明细"""
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False)  # 冗余:单据留痕,避免商品改名后失真
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)  # quantity × unit_price

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")


# ============ 财务流水与核销 ============

class FinanceEntry(Base):
    """财务流水 — 应收/应付/收款/付款统一模型

    状态由"已核销 vs 金额"推导:
      OPEN    未结清(settled_amount == 0)
      PARTIAL 部分结清(0 < settled_amount < amount)
      SETTLED 已结清(settled_amount == amount)
    """
    __tablename__ = "finance_entries"
    __table_args__ = (
        # 幂等兜底:同一来源单据 + 同一类型只能有一条(如一张销售订单只能生成一条应收)。
        # 注意:收款/付款流水的 source_order_no 允许为 NULL,SQLite 下 NULL 互不冲突。
        UniqueConstraint("source_order_no", "entry_type", name="uk_finance_source_type"),
        Index("ix_finance_entries_partner", "partner_name"),
        Index("ix_finance_entries_type", "entry_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_no = Column(String(50), nullable=False, unique=True, index=True)
    entry_type = Column(String(20), nullable=False)   # RECEIVABLE / PAYABLE / RECEIPT / PAYMENT
    partner_type = Column(String(20), nullable=False)  # CUSTOMER / SUPPLIER
    partner_id = Column(Integer, nullable=True)
    partner_name = Column(String(200), nullable=False)
    source_order_no = Column(String(50), nullable=True)  # 来源业务单据号
    amount = Column(Float, nullable=False)
    settled_amount = Column(Float, default=0, nullable=False)  # 已核销金额
    occurred_date = Column(Date, nullable=False)   # 发生日期
    due_date = Column(Date, nullable=True)         # 到期日(应收/应付)
    status = Column(String(20), default="OPEN", nullable=False)
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class FinanceSettlement(Base):
    """核销明细 — 一笔收款/付款核销到某张应收/应付的流水记录(支持部分核销多次核销)"""
    __tablename__ = "finance_settlements"
    __table_args__ = (
        Index("ix_settlements_receipt", "receipt_entry_id"),
        Index("ix_settlements_target", "target_entry_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_entry_id = Column(Integer, ForeignKey("finance_entries.id"), nullable=False)
    target_entry_id = Column(Integer, ForeignKey("finance_entries.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
