"""单据域 Schema"""
from datetime import datetime

from pydantic import Field, field_validator

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


# ============ 退货单（FBA / 买家 / 服务商） ============

class ReturnItemRequest(CamelModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    location_code: str = Field(..., min_length=1, max_length=50, description="目标库位")
    disposition: str = Field(default="RESELL", pattern="^(RESELL|RELABEL|SCRAP)$",
                             description="RESELL 转正品 / RELABEL 换标 / SCRAP 报废")


class ReturnOrderCreate(CamelModel):
    customer_id: int = Field(..., gt=0)
    source: str = Field(default="FBA", pattern="^(FBA|SELLER|CARRIER)$")
    items: list[ReturnItemRequest] = Field(..., min_length=1)
    remark: str | None = Field(default=None, max_length=200)


class ReturnOrderItemResponse(CamelModel):
    product_id: int
    product_name: str
    quantity: int
    location_code: str
    disposition: str
    batch_no: str | None = None


class ReturnOrderResponse(CamelModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: str
    source: str
    status: str
    remark: str | None = None
    items: list[ReturnOrderItemResponse] = []
    created_at: datetime


# ============ 波次拣货 ============

class WaveCreate(CamelModel):
    outbound_order_ids: list[int] = Field(..., min_length=1, description="待聚合的 PENDING 出库单 ID")
    remark: str | None = Field(default=None, max_length=200)


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

    @field_validator("change_qty")
    @classmethod
    def change_qty_not_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("调整数量不可为 0")
        return v


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
    count_id: int | None = None  # 由盘点单自动生成时回填
    remark: str | None = None
    items: list[StockAdjustmentItemResponse] = []
    created_at: datetime


# ============ 盘点单（库存准确率闭环） ============

class CountCreate(CamelModel):
    scope_type: str = Field(..., pattern="^(LOCATION|ZONE|PRODUCT|ALL)$",
                            description="LOCATION 库位 / ZONE 库区 / PRODUCT 商品 / ALL 全部")
    scope_value: str | None = Field(default=None, max_length=50,
                                    description="范围值：库位编码 / 库区ID / 商品ID（ALL 时省略）")
    remark: str | None = Field(default=None, max_length=200)


class CountSubmitItem(CamelModel):
    item_id: int = Field(..., gt=0)
    counted_qty: int = Field(..., ge=0, description="实盘数量")


class CountSubmit(CamelModel):
    items: list[CountSubmitItem] = Field(..., min_length=1)


class CountItemResponse(CamelModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    location_code: str
    system_qty: int
    counted_qty: int | None = None
    diff_qty: int | None = None  # counted_qty - system_qty（未录入时为 None）


class CountStatsResponse(CamelModel):
    total_items: int = 0
    accurate_items: int = 0
    accuracy_rate: float | None = None   # 库存准确率（账实相符 SKU×库位 / 总盘点行）
    location_count: int = 0
    accurate_location_count: int = 0
    location_accuracy_rate: float | None = None  # 库位准确率
    total_diff_qty: int = 0  # 差异总量（Σ|diff|）


class CountResponse(CamelModel):
    id: int
    count_no: str
    scope_type: str
    scope_value: str | None = None
    status: str
    remark: str | None = None
    items: list[CountItemResponse] = []
    stats: CountStatsResponse | None = None
    created_at: datetime
