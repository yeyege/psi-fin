from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ============ 通用 ============

class CamelModel(BaseModel):
    """统一 camelCase 序列化的基类。

    前端约定使用 camelCase（如 supplierName / productId），
    而后端 Python 习惯 snake_case。通过 alias_generator 让模型
    同时接受 camelCase 输入并按 camelCase 输出，避免前后端字段名不一致导致的 422 错误。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,   # 同时允许 snake_case 与 camelCase
        from_attributes=True,    # 允许从 ORM 对象属性构造
    )


class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: object = None


class PageResult(BaseModel):
    """分页结果"""
    list: list
    total: int
    page: int
    page_size: int


# ============ 商品（参考实现） ============

class ProductCreate(CamelModel):
    """创建商品请求"""
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    sku: str = Field(..., min_length=1, max_length=50, description="SKU编码")
    unit: str = Field(default="个", max_length=20)


class ProductUpdate(CamelModel):
    """更新商品请求"""
    name: str = Field(..., min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=20)


class ProductResponse(CamelModel):
    """商品响应"""
    id: int
    name: str
    sku: str
    unit: str
    created_at: datetime
    updated_at: datetime


# ============ 入库单（任务1） ============

class InboundItemRequest(CamelModel):
    """入库明细请求"""
    product_id: int = Field(..., gt=0, description="商品ID")
    quantity: int = Field(..., gt=0, description="入库数量")
    location_code: str = Field(..., min_length=1, max_length=50, description="目标库位编码")


class InboundOrderCreate(CamelModel):
    """创建入库单请求"""
    supplier_name: str = Field(..., min_length=1, max_length=200, description="供应商名称")
    items: list[InboundItemRequest] = Field(..., min_length=1, description="入库明细")


class InboundItemResponse(CamelModel):
    """入库明细响应"""
    product_id: int
    product_name: str
    quantity: int
    location_code: str


class InboundOrderResponse(CamelModel):
    """入库单响应"""
    id: int
    order_no: str
    supplier_name: str
    status: str
    items: list[InboundItemResponse] = []
    created_at: datetime


# ============ 库存查询（任务2） ============

class InventoryResponse(CamelModel):
    """库存查询响应"""
    product_id: int
    product_name: str
    sku: str
    location_code: str
    warehouse_name: str | None = None
    quantity: int
    updated_at: datetime


# ============ 出库单（选做 A） ============

class OutboundItemRequest(CamelModel):
    """出库明细请求"""
    product_id: int = Field(..., gt=0, description="商品ID")
    quantity: int = Field(..., gt=0, description="出库数量")
    location_code: str = Field(..., min_length=1, max_length=50, description="来源库位编码")


class OutboundOrderCreate(CamelModel):
    """创建出库单请求"""
    customer_name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    items: list[OutboundItemRequest] = Field(..., min_length=1, description="出库明细")


class OutboundItemResponse(CamelModel):
    """出库明细响应"""
    product_id: int
    product_name: str
    quantity: int
    location_code: str


class OutboundOrderResponse(CamelModel):
    """出库单响应"""
    id: int
    order_no: str
    customer_name: str
    status: str
    items: list[OutboundItemResponse] = []
    created_at: datetime
