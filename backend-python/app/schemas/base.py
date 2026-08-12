"""通用 + 基础数据 Schema"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """统一 camelCase 序列化基类。

    前端约定 camelCase（supplierName / productId），后端 Python 习惯 snake_case。
    通过 alias_generator 同时接受 camelCase 输入并按 camelCase 输出。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: object = None


class PageResult(BaseModel):
    list: list
    total: int
    page: int
    pageSize: int


# ============ 商品 SKU ============

class ProductCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    fns_ku: str | None = Field(default=None, max_length=50)
    case_qty: int = Field(default=1, ge=1)
    unit: str = Field(default="个", max_length=20)
    width: float = Field(default=0, ge=0)
    height: float = Field(default=0, ge=0)
    length: float = Field(default=0, ge=0)
    weight: float = Field(default=0, ge=0)


class ProductUpdate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    fns_ku: str | None = Field(default=None, max_length=50)
    case_qty: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=20)
    width: float | None = Field(default=None, ge=0)
    height: float | None = Field(default=None, ge=0)
    length: float | None = Field(default=None, ge=0)
    weight: float | None = Field(default=None, ge=0)
    status: str | None = None


class ProductResponse(CamelModel):
    id: int
    name: str
    sku: str
    fns_ku: str | None = None
    case_qty: int = 1
    unit: str
    width: float
    height: float
    length: float
    weight: float
    status: str
    created_at: datetime
    updated_at: datetime


# ============ 客户（分层管理 A/B/C） ============

class CustomerCreate(CamelModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    tier: str = Field(default="C", pattern="^[ABC]$")
    contact: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)


class CustomerUpdate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    tier: str = Field(default="C", pattern="^[ABC]$")
    contact: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    status: str | None = None


class CustomerResponse(CamelModel):
    id: int
    code: str
    name: str
    tier: str
    contact: str | None = None
    phone: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


# ============ 仓库 ============

class WarehouseCreate(CamelModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class WarehouseResponse(CamelModel):
    id: int
    code: str
    name: str
    status: str


# ============ 库区 ============

class ZoneCreate(CamelModel):
    warehouse_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    zone_type: str = Field(default="GOODS", pattern="^(GOODS|DEFECT)$")


class ZoneResponse(CamelModel):
    id: int
    warehouse_id: int
    code: str
    name: str
    zone_type: str


# ============ 库位 ============

class LocationCreate(CamelModel):
    zone_id: int = Field(..., gt=0)
    warehouse_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=50)
    priority: int = Field(default=0, ge=0)


class LocationResponse(CamelModel):
    id: int
    zone_id: int
    warehouse_id: int
    code: str
    priority: int
    status: str
