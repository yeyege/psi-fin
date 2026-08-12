"""单据域 Schema"""
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


# ============ 入库单 ============

class InboundItemRequest(CamelModel):
    product_id: int = Field(..., gt=0, description="商品ID")
    quantity: int = Field(..., gt=0, description="入库数量")
    location_code: str = Field(..., min_length=1, max_length=50, description="目标库位编码")


class InboundOrderCreate(CamelModel):
    supplier_name: str = Field(..., min_length=1, max_length=200)
    items: list[InboundItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class InboundOrderItemResponse(CamelModel):
    product_id: int
    product_name: str
    quantity: int
    location_code: str
    batch_no: str | None = None


class InboundOrderResponse(CamelModel):
    id: int
    order_no: str
    supplier_name: str
    status: str
    remark: str | None = None
    items: list[InboundOrderItemResponse] = []
    created_at: datetime


# ============ 出库单 ============

class OutboundItemRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    location_code: str = Field(..., min_length=1, max_length=50)


class OutboundOrderCreate(CamelModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    items: list[OutboundItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class OutboundOrderItemResponse(CamelModel):
    product_id: int
    product_name: str
    quantity: int
    location_code: str


class OutboundOrderResponse(CamelModel):
    id: int
    order_no: str
    customer_name: str
    status: str
    remark: str | None = None
    items: list[OutboundOrderItemResponse] = []
    created_at: datetime


# ============ 移库单 ============

class StockTransferItemRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    from_location_code: str = Field(..., min_length=1, max_length=50)
    to_location_code: str = Field(..., min_length=1, max_length=50)


class StockTransferCreate(CamelModel):
    items: list[StockTransferItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class StockTransferItemResponse(CamelModel):
    product_id: int
    product_name: str
    quantity: int
    from_location_code: str
    to_location_code: str


class StockTransferResponse(CamelModel):
    id: int
    order_no: str
    status: str
    remark: str | None = None
    items: list[StockTransferItemResponse] = []
    created_at: datetime


# ============ 库存调整 ============

class StockAdjustmentItemRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    location_code: str = Field(..., min_length=1, max_length=50)
    change_qty: int = Field(..., description="正=盘盈(+)，负=盘亏(-)")


class StockAdjustmentCreate(CamelModel):
    items: list[StockAdjustmentItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class StockAdjustmentItemResponse(CamelModel):
    product_id: int
    product_name: str
    location_code: str
    change_qty: int


class StockAdjustmentResponse(CamelModel):
    id: int
    order_no: str
    status: str
    remark: str | None = None
    items: list[StockAdjustmentItemResponse] = []
    created_at: datetime
