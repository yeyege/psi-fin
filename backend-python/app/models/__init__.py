"""ORM 模型包 — 对标领星WMS重构

业务模型划分：
- base.py      : 基础数据（商品/仓库/库区/库位）
- inventory.py : 库存域（批次/库存行/库存流水）
- orders.py    : 单据域（入库/出库/移库/库存调整）
"""
from app.models.base import Product, Warehouse, Zone, Location
from app.models.inventory import Batch, Inventory, InventoryFlow
from app.models.orders import (
    InboundOrder,
    InboundOrderItem,
    OutboundOrder,
    OutboundOrderItem,
    StockTransfer,
    StockTransferItem,
    StockAdjustment,
    StockAdjustmentItem,
)

__all__ = [
    "Product",
    "Warehouse",
    "Zone",
    "Location",
    "Batch",
    "Inventory",
    "InventoryFlow",
    "InboundOrder",
    "InboundOrderItem",
    "OutboundOrder",
    "OutboundOrderItem",
    "StockTransfer",
    "StockTransferItem",
    "StockAdjustment",
    "StockAdjustmentItem",
]
