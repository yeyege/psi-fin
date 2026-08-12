"""数据看板聚合服务 — 首页统计

对标领星 WMS 数据看板：
- 各类单据数量（今日/待处理）
- 库存总量与低库存预警
- 基础数据统计（商品/客户）
"""
from datetime import datetime, date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Product, Customer, Inventory, InboundOrder, OutboundOrder,
)


def dashboard_summary(db: Session) -> dict:
    today = datetime.combine(date.today(), datetime.min.time())

    def _today_count(model):
        return db.query(model).filter(model.created_at >= today).count()

    def _status_count(model, statuses):
        return db.query(model).filter(model.status.in_(statuses)).count()

    # 库存总量与低库存商品数（总库存 < 10）
    total_qty = (
        db.query(func.coalesce(func.sum(Inventory.available_qty + Inventory.locked_qty), 0))
        .scalar()
    )
    low_stock_products = (
        db.query(Product)
        .join(Inventory, Inventory.product_id == Product.id)
        .group_by(Product.id)
        .having(func.sum(Inventory.available_qty + Inventory.locked_qty) < 10)
        .count()
    )

    return {
        "todayInboundCount": _today_count(InboundOrder),
        "todayOutboundCount": _today_count(OutboundOrder),
        "pendingInboundCount": _status_count(InboundOrder, ["PENDING"]),
        "pendingOutboundCount": _status_count(OutboundOrder, ["PENDING", "PICKED"]),
        "totalInventoryQty": int(total_qty),
        "lowStockProductCount": int(low_stock_products),
        "activeProductCount": db.query(Product).filter(Product.status == "ACTIVE").count(),
        "activeCustomerCount": db.query(Customer).filter(Customer.status == "ACTIVE").count(),
    }
