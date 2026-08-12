"""数据看板聚合服务单元测试（MVP M3）

覆盖：统计数字随业务数据变化而正确变化。
"""
from datetime import datetime

from app.models import InboundOrder, OutboundOrder, Batch, Inventory
from app.services import dashboard_service, inventory_service


def _mk_order(db, model, status, days_ago=0):
    from datetime import timedelta
    o = model(order_no=f"T-{status}-{model.__name__}-{days_ago}-{datetime.now().microsecond}",
              status=status)
    o.created_at = datetime.now() - timedelta(days=days_ago)
    db.add(o)
    db.flush()
    return o


def test_dashboard_empty(db_session):
    s = dashboard_service.dashboard_summary(db_session)
    assert s["todayInboundCount"] == 0
    assert s["totalInventoryQty"] == 0
    assert s["activeProductCount"] == 2  # conftest 注入 2 个商品


def test_dashboard_counts_today_orders(db_session):
    _mk_order(db_session, InboundOrder, "PENDING")
    _mk_order(db_session, InboundOrder, "COMPLETED")
    _mk_order(db_session, OutboundOrder, "PENDING")
    _mk_order(db_session, OutboundOrder, "SHIPPED")
    db_session.commit()

    s = dashboard_service.dashboard_summary(db_session)
    assert s["todayInboundCount"] == 2
    assert s["todayOutboundCount"] == 2
    assert s["pendingInboundCount"] == 1
    assert s["pendingOutboundCount"] == 1


def test_dashboard_inventory_and_low_stock(db_session):
    # 商品1 入库 100 → 库存总量 100，非低库存
    inventory_service.add_stock(
        db_session, product_id=1, location_code="LOC-01", batch_id=None, quantity=100,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="T-DASH-IN",
    )
    # 商品2 入库 5 → 低库存
    inventory_service.add_stock(
        db_session, product_id=2, location_code="LOC-02", batch_id=None, quantity=5,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="T-DASH-IN2",
    )
    s = dashboard_service.dashboard_summary(db_session)
    assert s["totalInventoryQty"] == 105
    assert s["lowStockProductCount"] == 1
