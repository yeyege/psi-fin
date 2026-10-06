"""库存域 Schema"""
from datetime import datetime

from app.schemas.base import CamelModel


class BatchResponse(CamelModel):
    id: int
    batch_no: str
    product_id: int
    product_name: str = ""
    sku: str = ""
    inbound_date: datetime
    manufacture_date: datetime | None = None
    expiry_date: datetime | None = None
    # 生命周期字段（p0-2 tasks 3.2）：状态口径由 inventory_service.batch_lifecycle 单点计算
    age_days: int | None = None
    batch_status: str | None = None   # NORMAL / EXPIRING / EXPIRED / AGING


class InventoryRowResponse(CamelModel):
    """按库位明细（按库位视角）"""
    product_id: int
    product_name: str
    sku: str
    location_code: str
    warehouse_id: int
    warehouse_name: str
    batch_no: str | None = None
    available_qty: int
    locked_qty: int
    total_qty: int
    updated_at: datetime
    # 批次效期与状态（p0-2 tasks 3.1）：未挂批次的库存行五列全为 None，
    # 而不是回 0 天或被误标为 NORMAL
    manufacture_date: datetime | None = None
    expiry_date: datetime | None = None
    days_to_expiry: int | None = None
    age_days: int | None = None
    batch_status: str | None = None


class InventoryProductViewResponse(CamelModel):
    """按产品汇总（按产品视角：仓库维度可用/锁定合计）"""
    product_id: int
    product_name: str
    sku: str
    warehouse_id: int
    warehouse_name: str
    available_qty: int
    locked_qty: int
    total_qty: int
    updated_at: datetime


class InventoryFlowResponse(CamelModel):
    id: int
    flow_type: str
    order_type: str
    order_no: str
    product_id: int
    product_name: str
    sku: str
    location_code: str | None = None
    batch_no: str | None = None
    quantity: int
    before_qty: int | None = None
    after_qty: int | None = None
    remark: str | None = None
    created_at: datetime
