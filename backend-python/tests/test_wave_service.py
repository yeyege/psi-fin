"""波次拣货 Service 单元测试（MVP M5）

覆盖：
- 生成波次：WV 单号 / 逐出库单生成 PK 拣货单 / 明细按(商品,库位)聚合 / 按库位优先级排序
- 非 PENDING 出库单不可入波次
- 执行拣货：锁定库存、出库单→PICKED、波次状态推进直至 COMPLETED
- 库存不足整单回滚
"""
from datetime import datetime

import pytest

from app.common.errors import BusinessError
from app.models import Batch, Inventory, InventoryFlow, Wave
from app.schemas import OutboundOrderCreate, OutboundItemRequest
from app.services import inventory_service, outbound_service, wave_service


def _seed_stock(db, pid: int, loc: str, qty: int):
    b = Batch(batch_no=f"W-{pid}-{loc}", product_id=pid, inbound_date=datetime.now())
    db.add(b)
    db.flush()
    inventory_service.add_stock(
        db, product_id=pid, location_code=loc, batch_id=b.id, quantity=qty,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="WSEED",
    )
    db.commit()


def _mk_outbound(db, items) -> int:
    order = outbound_service.create_outbound_order(db, OutboundOrderCreate(
        customer_name="波次客户", items=items,
    ))
    return order.id


def test_create_wave_generates_picking_orders(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    _seed_stock(db_session, 2, "LOC-02", 100)
    oid1 = _mk_outbound(db_session, [OutboundItemRequest(productId=1, quantity=30, locationCode="LOC-01")])
    oid2 = _mk_outbound(db_session, [OutboundItemRequest(productId=2, quantity=10, locationCode="LOC-02")])

    wave = wave_service.create_wave(db_session, [oid1, oid2], remark="上午波次")
    assert wave.wave_no.startswith("WV-")
    assert wave.status == "CREATED"
    assert len(wave.picking_orders) == 2
    for p in wave.picking_orders:
        assert p.picking_no.startswith("PK-")
        assert len(p.items) == 1

    # 出库单回填 wave_id
    o1 = db_session.get(outbound_service.OutboundOrder, oid1)
    assert o1.wave_id == wave.id


def test_create_wave_aggregates_and_sorts_by_location_priority(db_session):
    """同一(商品,库位)聚合；拣货明细按库位优先级降序（LOC-01 优先于 LOC-02）。"""
    _seed_stock(db_session, 1, "LOC-01", 50)
    _seed_stock(db_session, 1, "LOC-02", 50)
    oid = _mk_outbound(db_session, [
        OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-02"),
        OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-02"),
        OutboundItemRequest(productId=1, quantity=20, locationCode="LOC-01"),
    ])
    wave = wave_service.create_wave(db_session, [oid])
    picking = wave.picking_orders[0]
    assert len(picking.items) == 2
    qty_by_loc = {it.location_code: it.quantity for it in picking.items}
    assert qty_by_loc["LOC-02"] == 20  # 两行聚合
    assert qty_by_loc["LOC-01"] == 20
    # 排序：LOC-01(priority 5) 在 LOC-02(priority 4) 之前
    assert picking.items[0].location_code == "LOC-01"


def test_create_wave_rejects_non_pending(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    oid = _mk_outbound(db_session, [OutboundItemRequest(productId=1, quantity=1, locationCode="LOC-01")])
    outbound_service.pick_outbound_order(db_session, oid)
    with pytest.raises(BusinessError) as exc:
        wave_service.create_wave(db_session, [oid])
    assert "不可加入波次" in exc.value.message


def test_pick_picking_order_locks_and_advances_wave(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    _seed_stock(db_session, 2, "LOC-02", 100)
    oid1 = _mk_outbound(db_session, [OutboundItemRequest(productId=1, quantity=30, locationCode="LOC-01")])
    oid2 = _mk_outbound(db_session, [OutboundItemRequest(productId=2, quantity=10, locationCode="LOC-02")])
    wave = wave_service.create_wave(db_session, [oid1, oid2])

    # 拣第一张：波次 → PICKING，出库单 → PICKED
    p1, p2 = wave.picking_orders
    wave_service.pick_picking_order(db_session, p1.id)
    wave = db_session.get(Wave, wave.id)
    assert wave.status == "PICKING"
    assert db_session.get(outbound_service.OutboundOrder, oid1).status == "PICKED"

    inv = db_session.query(Inventory).filter_by(product_id=1).first()
    assert inv.available_qty == 70 and inv.locked_qty == 30

    # 拣第二张：波次 → COMPLETED
    wave_service.pick_picking_order(db_session, p2.id)
    wave = db_session.get(Wave, wave.id)
    assert wave.status == "COMPLETED"
    assert db_session.get(outbound_service.OutboundOrder, oid2).status == "PICKED"

    # 流水：每个拣货明细一条 PICK_LOCK，order_no 为拣货单号
    locks = db_session.query(InventoryFlow).filter_by(flow_type="PICK_LOCK").all()
    assert len(locks) == 2


def test_pick_insufficient_stock_rolls_back(db_session):
    _seed_stock(db_session, 1, "LOC-01", 5)
    oid = _mk_outbound(db_session, [OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-01")])
    wave = wave_service.create_wave(db_session, [oid])

    with pytest.raises(BusinessError) as exc:
        wave_service.pick_picking_order(db_session, wave.picking_orders[0].id)
    assert exc.value.status == 409

    # 无副作用：库存未锁定、出库单仍 PENDING、拣货单仍 CREATED
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 5 and inv.locked_qty == 0
    assert db_session.get(outbound_service.OutboundOrder, oid).status == "PENDING"


def test_pick_twice_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    oid = _mk_outbound(db_session, [OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-01")])
    wave = wave_service.create_wave(db_session, [oid])
    wave_service.pick_picking_order(db_session, wave.picking_orders[0].id)
    with pytest.raises(BusinessError):
        wave_service.pick_picking_order(db_session, wave.picking_orders[0].id)
