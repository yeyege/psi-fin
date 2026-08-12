"""库存核心 Service 单元测试（对标领星WMS）

覆盖：
- add_stock：新建库存行 / 累加已有行 / 强制写流水
- deduct_stock：跨批次先扣早期批次（FIFO）/ 库存不足返回 False 且无副作用
- lock_stock / ship_stock：可用量→锁定量 → 发货扣减；不足返回 False
- 查询：product 视图按(商品,仓库)汇总、location 视图含批次
"""
from datetime import datetime

from app.models import Batch, Inventory, InventoryFlow
from app.services import inventory_service


def _add_batch(db, pid: int, batch_no: str) -> Batch:
    b = Batch(batch_no=batch_no, product_id=pid, inbound_date=datetime.now())
    db.add(b)
    db.flush()
    return b


def _add_stock(db, pid: int, loc: str, qty: int, batch_id=None) -> Inventory:
    return inventory_service.add_stock(
        db, product_id=pid, location_code=loc, batch_id=batch_id, quantity=qty,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND,
        order_no="T-IN-1",
    )


def test_add_stock_creates_row_and_flow(db_session):
    inv = _add_stock(db_session, 1, "LOC-01", 100)
    assert inv.available_qty == 100
    assert inv.locked_qty == 0

    flows = db_session.query(InventoryFlow).all()
    assert len(flows) == 1
    assert flows[0].flow_type == "INBOUND"
    assert flows[0].before_qty == 0
    assert flows[0].after_qty == 100
    assert flows[0].quantity == 100


def test_add_stock_accumulates_same_row(db_session):
    """同(商品,库位,批次)重复入库应累加在同一行，且每次写流水。"""
    _add_stock(db_session, 1, "LOC-01", 100)
    inv = _add_stock(db_session, 1, "LOC-01", 50)
    assert inv.available_qty == 150
    assert db_session.query(Inventory).count() == 1
    assert db_session.query(InventoryFlow).count() == 2


def test_deduct_stock_cross_batch_fifo(db_session):
    """跨批次扣减：先扣早期批次（按入库行先后）。"""
    b1 = _add_batch(db_session, 1, "B-1")
    b2 = _add_batch(db_session, 1, "B-2")
    _add_stock(db_session, 1, "LOC-01", 30, batch_id=b1.id)
    _add_stock(db_session, 1, "LOC-01", 70, batch_id=b2.id)

    ok = inventory_service.deduct_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=50,
        flow_type=inventory_service.FLOW_TYPE_MOVE_OUT,
        order_type=inventory_service.ORDER_TYPE_TRANSFER, order_no="T-MV",
    )
    assert ok is True
    rows = db_session.query(Inventory).order_by(Inventory.id.asc()).all()
    assert rows[0].available_qty == 0   # 早期批次先被扣完
    assert rows[1].available_qty == 50


def test_deduct_stock_insufficient_returns_false(db_session):
    _add_stock(db_session, 1, "LOC-01", 10)
    ok = inventory_service.deduct_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=11,
        flow_type=inventory_service.FLOW_TYPE_MOVE_OUT,
        order_type=inventory_service.ORDER_TYPE_TRANSFER, order_no="T-MV",
    )
    assert ok is False
    # 无副作用：库存未变、未新增流水
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 10
    assert db_session.query(InventoryFlow).count() == 1


def test_lock_and_ship_stock(db_session):
    _add_stock(db_session, 1, "LOC-01", 100)

    ok = inventory_service.lock_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=30,
        order_type=inventory_service.ORDER_TYPE_OUTBOUND, order_no="T-OUT",
    )
    assert ok is True
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 70
    assert inv.locked_qty == 30

    ok = inventory_service.ship_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=30,
        order_type=inventory_service.ORDER_TYPE_OUTBOUND, order_no="T-OUT",
    )
    assert ok is True
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 70
    assert inv.locked_qty == 0

    # 流水类型完整：PICK_LOCK 与 OUTBOUND
    types = {f.flow_type for f in db_session.query(InventoryFlow).all()}
    assert "PICK_LOCK" in types and "OUTBOUND" in types


def test_lock_stock_insufficient(db_session):
    _add_stock(db_session, 1, "LOC-01", 5)
    ok = inventory_service.lock_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=10,
        order_type=inventory_service.ORDER_TYPE_OUTBOUND, order_no="T-OUT",
    )
    assert ok is False
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 5
    assert inv.locked_qty == 0


def test_query_inventory_product_view_aggregates(db_session):
    """product 视图按 (商品,仓库) 汇总，跨库位合并。"""
    b1 = _add_batch(db_session, 1, "B-1")
    _add_stock(db_session, 1, "LOC-01", 30, batch_id=b1.id)
    _add_stock(db_session, 1, "LOC-02", 20)

    res = inventory_service.query_inventory(db_session, view="product")
    assert res["total"] == 1
    row = res["list"][0]
    assert row["sku"] == "T-001"
    assert row["availableQty"] == 50
    assert row["totalQty"] == 50


def test_query_inventory_location_view_has_batch(db_session):
    b1 = _add_batch(db_session, 1, "B-1")
    _add_stock(db_session, 1, "LOC-01", 30, batch_id=b1.id)
    _add_stock(db_session, 2, "LOC-02", 20)

    res = inventory_service.query_inventory(db_session, view="location")
    assert res["total"] == 2
    by_loc = {r["locationCode"]: r for r in res["list"]}
    assert by_loc["LOC-01"]["batchNo"] == "B-1"
    assert by_loc["LOC-01"]["availableQty"] == 30


def test_query_inventory_keyword_and_warehouse_filter(db_session):
    b1 = _add_batch(db_session, 1, "B-1")
    _add_stock(db_session, 1, "LOC-01", 30, batch_id=b1.id)
    _add_stock(db_session, 2, "LOC-02", 20)

    res = inventory_service.query_inventory(db_session, view="location", keyword="T-001")
    assert res["total"] == 1
    res = inventory_service.query_inventory(db_session, view="location", warehouse_id=1)
    assert res["total"] == 2


def test_query_flows_traceable(db_session):
    _add_stock(db_session, 1, "LOC-01", 100)
    inventory_service.lock_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=30,
        order_type=inventory_service.ORDER_TYPE_OUTBOUND, order_no="T-OUT",
    )
    res = inventory_service.query_flows(db_session, product_id=1)
    assert res["total"] == 2
    assert res["list"][0]["flowType"] == "PICK_LOCK"
    assert res["list"][0]["sku"] == "T-001"
    assert res["list"][0]["quantity"] == 30
