"""Pydantic Schema 包

统一使用 camelCase 与前端约定对齐（见 common.CamelModel）。
"""
from app.schemas.base import CamelModel, ApiResponse, PageResult
from app.schemas.base import (
    ProductCreate, ProductUpdate, ProductResponse,
    CustomerCreate, CustomerUpdate, CustomerResponse,
    WarehouseCreate, WarehouseResponse,
    ZoneCreate, ZoneResponse,
    LocationCreate, LocationResponse,
)
from app.schemas.inventory import (
    BatchResponse,
    InventoryRowResponse,
    InventoryProductViewResponse,
    InventoryFlowResponse,
)
from app.schemas.orders import (
    InboundItemRequest, InboundOrderCreate, InboundOrderItemResponse, InboundOrderResponse,
    OutboundItemRequest, OutboundOrderCreate, OutboundOrderItemResponse, OutboundOrderResponse,
    ReturnItemRequest, ReturnOrderCreate, ReturnOrderItemResponse, ReturnOrderResponse,
    WaveCreate,
    StockTransferItemRequest, StockTransferCreate, StockTransferResponse,
    StockAdjustmentItemRequest, StockAdjustmentCreate, StockAdjustmentResponse,
    CountCreate, CountSubmitItem, CountSubmit, CountItemResponse,
    CountStatsResponse, CountResponse,
)
from app.schemas.auth import (
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, LoginResponse,
)

__all__ = [
    "CamelModel", "ApiResponse", "PageResult",
    "ProductCreate", "ProductUpdate", "ProductResponse",
    "CustomerCreate", "CustomerUpdate", "CustomerResponse",
    "WarehouseCreate", "WarehouseResponse",
    "ZoneCreate", "ZoneResponse",
    "LocationCreate", "LocationResponse",
    "BatchResponse",
    "InventoryRowResponse",
    "InventoryProductViewResponse",
    "InventoryFlowResponse",
    "InboundItemRequest", "InboundOrderCreate", "InboundOrderItemResponse", "InboundOrderResponse",
    "OutboundItemRequest", "OutboundOrderCreate", "OutboundOrderItemResponse", "OutboundOrderResponse",
    "StockTransferItemRequest", "StockTransferCreate", "StockTransferResponse",
    "StockAdjustmentItemRequest", "StockAdjustmentCreate", "StockAdjustmentResponse",
    "CountCreate", "CountSubmitItem", "CountSubmit", "CountItemResponse",
    "CountStatsResponse", "CountResponse",
    "ReturnItemRequest", "ReturnOrderCreate", "ReturnOrderItemResponse", "ReturnOrderResponse",
    "WaveCreate",
    "UserCreate", "UserUpdate", "UserResponse",
    "LoginRequest", "LoginResponse",
]
