"""ORM 模型包 — 对标领星WMS重构

业务模型划分：
- base.py      : 基础数据（商品/仓库/库区/库位）
- inventory.py : 库存域（批次/库存行/库存流水）
- orders.py    : 单据域（入库/出库/移库/库存调整）
- finance.py    : 业财域（销售订单/财务流水/核销）
- accounting.py : 会计内核（科目表/凭证/期间），见 openspec oss-finance-ai-platform
"""
from app.models.base import Product, Customer, Warehouse, Zone, Location
from app.models.inventory import Batch, Inventory, InventoryFlow
from app.models.auth import User, AuthToken
from app.models.orders import (
    InboundOrder,
    InboundOrderItem,
    OutboundOrder,
    OutboundOrderItem,
    ReturnOrder,
    ReturnOrderItem,
    Wave,
    PickingOrder,
    PickingOrderItem,
    StockTransfer,
    StockTransferItem,
    StockAdjustment,
    StockAdjustmentItem,
    CycleCount,
    CycleCountItem,
)
from app.models.finance import (
    SalesOrder,
    SalesOrderItem,
    FinanceEntry,
    FinanceSettlement,
)
from app.models.accounting import (
    Account,
    Period,
    Voucher,
    VoucherLine,
)

__all__ = [
    "Product",
    "Customer",
    "Warehouse",
    "Zone",
    "Location",
    "User",
    "AuthToken",
    "Batch",
    "Inventory",
    "InventoryFlow",
    "InboundOrder",
    "InboundOrderItem",
    "OutboundOrder",
    "OutboundOrderItem",
    "ReturnOrder",
    "ReturnOrderItem",
    "Wave",
    "PickingOrder",
    "PickingOrderItem",
    "StockTransfer",
    "StockTransferItem",
    "StockAdjustment",
    "StockAdjustmentItem",
    "CycleCount",
    "CycleCountItem",
    "SalesOrder",
    "SalesOrderItem",
    "FinanceEntry",
    "FinanceSettlement",
    "Account",
    "Period",
    "Voucher",
    "VoucherLine",
]
