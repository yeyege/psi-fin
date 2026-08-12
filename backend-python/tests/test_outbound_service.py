"""出库单 Service 单元测试 — 状态机 PENDING → PICKED → SHIPPED（防超卖）

对标领星WMS：
- 创建出库单（PENDING）不改变库存；
- 拣货 pick：available → locked（原子锁定防超卖），库存不足整单回滚；
- 发货 ship：扣减 locked，写 OUTBOUND 流水。
"""
from datetime import datetime

import pytest

from app.common.errors import BusinessError
from app.models import Batch, Inventory, InventoryFlow, OutboundOrder
from app.schemas import OutboundOrderCreate, OutboundItemRequest
from app.services import inventory_service, outbound_service


def _seed_stock(db, pid: int, loc: str, qty: int):
    b = Batch(batch_no=f"B-{pid}-{loc}", product_id=pid, inbound_date=datetime.now())
    db.add(b)
    db.flush()
    inventory_service.add_stock(
        db, product_id=pid, location_code=loc, batch_id=b.id, quantity=qty,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="SEED",
    )
    db.commit()


def _make_req(**kw) -> OutboundOrderCreate:
    defaults = {
        "customerName": "客户A",
        "items": [OutboundItemRequest(productId=1, quantity=30, locationCode="LOC-01")],
    }
    defaults.update(kw)
    return OutboundOrderCreate(**defaults)


def test_create_outbound_pending_without_stock_change(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())

    today = datetime.now().strftime("%Y%m%d")
    assert order.order_no == f"OUT-{today}-001"
    assert order.status == "PENDING"
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 100  # 创建不扣库存


def test_pick_locks_stock(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())

    order = outbound_service.pick_outbound_order(db_session, order.id)
    assert order.status == "PICKED"
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 70
    assert inv.locked_qty == 30


def test_pick_insufficient_stock_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 5)
    order = outbound_service.create_outbound_order(
        db_session, _make_req(items=[OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-01")])
    )
    with pytest.raises(BusinessError) as exc:
        outbound_service.pick_outbound_order(db_session, order.id)
    assert exc.value.status == 409
    # 无副作用：库存未锁定、单据状态不变
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 5 and inv.locked_qty == 0
    assert order.status == "PENDING"


def test_ship_deducts_locked_stock(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())
    outbound_service.pick_outbound_order(db_session, order.id)

    order = outbound_service.ship_outbound_order(db_session, order.id)
    assert order.status == "SHIPPED"
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 70
    assert inv.locked_qty == 0
    # 流水含 PICK_LOCK 与 OUTBOUND
    types = {f.flow_type for f in db_session.query(InventoryFlow).all()}
    assert "PICK_LOCK" in types and "OUTBOUND" in types


def test_ship_without_pick_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())
    with pytest.raises(BusinessError):
        outbound_service.ship_outbound_order(db_session, order.id)


def test_pick_rollback_on_partial_failure(db_session):
    """多明细中一条库存不足时，整单回滚：已锁定的明细也应回滚。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    _seed_stock(db_session, 2, "LOC-02", 1)
    order = outbound_service.create_outbound_order(db_session, _make_req(items=[
        OutboundItemRequest(productId=1, quantity=50, locationCode="LOC-01"),
        OutboundItemRequest(productId=2, quantity=999, locationCode="LOC-02"),
    ]))
    with pytest.raises(BusinessError):
        outbound_service.pick_outbound_order(db_session, order.id)

    inv1 = db_session.query(Inventory).filter_by(product_id=1).first()
    assert inv1.available_qty == 100 and inv1.locked_qty == 0
    assert order.status == "PENDING"


def test_create_outbound_invalid_product(db_session):
    with pytest.raises(BusinessError) as exc:
        outbound_service.create_outbound_order(db_session, _make_req(
            items=[OutboundItemRequest(productId=999, quantity=1, locationCode="LOC-01")]
        ))
    assert exc.value.status == 404
    assert db_session.query(OutboundOrder).count() == 0
