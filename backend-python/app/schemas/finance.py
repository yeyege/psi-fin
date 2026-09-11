"""业财一体 Schema — 销售订单 / 财务流水 / 核销 / 驾驶舱"""
from datetime import date, datetime

from pydantic import Field

from app.schemas.base import CamelModel


# ============ 销售订单 ============

class SalesOrderItemRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, description="数量")
    unit_price: float = Field(..., ge=0, description="单价")


class SalesOrderCreate(CamelModel):
    customer_id: int = Field(..., gt=0)
    credit_days: int = Field(default=0, ge=0, description="账期(天)，发货后用于计算应收到期日")
    items: list[SalesOrderItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class SalesOrderUpdate(CamelModel):
    """仅草稿状态可编辑；items 传则整体替换并重算金额"""
    credit_days: int | None = Field(default=None, ge=0)
    items: list[SalesOrderItemRequest] | None = None
    remark: str | None = Field(default=None, max_length=200)


class SalesOrderShip(CamelModel):
    outbound_order_no: str | None = Field(default=None, max_length=50,
                                          description="关联出库单号(可空，一期预留)")


class SalesOrderItemResponse(CamelModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    amount: float


class SalesOrderResponse(CamelModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: str
    status: str
    credit_days: int
    total_amount: float
    outbound_order_no: str | None = None
    shipped_at: datetime | None = None
    remark: str | None = None
    items: list[SalesOrderItemResponse] = []
    created_at: datetime


# ============ 财务流水 / 核销 ============

class SettlementAllocation(CamelModel):
    target_entry_id: int = Field(..., gt=0, description="目标应收/应付流水 ID")
    amount: float = Field(..., gt=0, description="本次核销金额")


class ReceiptCreate(CamelModel):
    partner_type: str = Field(default="CUSTOMER", pattern="^(CUSTOMER|SUPPLIER)$")
    partner_id: int | None = Field(default=None, gt=0)
    partner_name: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, description="到账金额（可大于核销金额，差额为预收）")
    occurred_date: date | None = Field(default=None, description="收款日期，默认今天")
    remark: str | None = Field(default=None, max_length=200)
    allocations: list[SettlementAllocation] = Field(default_factory=list)


class AllocateRequest(CamelModel):
    allocations: list[SettlementAllocation] = Field(..., min_length=1)


class FinanceEntryResponse(CamelModel):
    id: int
    entry_no: str
    entry_type: str
    partner_type: str
    partner_id: int | None = None
    partner_name: str
    source_order_no: str | None = None
    amount: float
    settled_amount: float
    outstanding: float
    occurred_date: date
    due_date: date | None = None
    status: str
    overdue: bool = False
    remark: str | None = None
    created_at: datetime


class AgingRowResponse(CamelModel):
    partner_name: str
    receivable_total: float
    settled_total: float
    balance: float
    not_due: float
    days1to30: float
    days31to60: float
    days60plus: float


# ============ 经营驾驶舱 ============

class ExecutiveSummaryResponse(CamelModel):
    receivable_total: float
    received_total: float
    outstanding_total: float
    overdue_total: float
    order_count: int
    order_amount: float


class TrendPointResponse(CamelModel):
    date: str
    order_amount: float
    receipt_amount: float
