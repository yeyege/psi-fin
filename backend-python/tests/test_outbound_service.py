"""出库单 Service 单元测试 — 状态机 PENDING → PICKED → SHIPPED（防超卖）

对标领星WMS：
- 创建出库单（PENDING）不改变库存；
- 拣货 pick：available → locked（原子锁定防超卖），库存不足整单回滚；
- 发货 ship：扣减 locked，写 OUTBOUND 流水。
"""
from datetime import datetime
import threading

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

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
    outbound_service.review_outbound_order(db_session, order.id)

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


def test_ship_without_review_rejected(db_session):
    """PICKED 未复核不可直接发货（复核验货是发货前置环节）。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())
    outbound_service.pick_outbound_order(db_session, order.id)
    with pytest.raises(BusinessError):
        outbound_service.ship_outbound_order(db_session, order.id)
    inv = db_session.query(Inventory).first()
    assert inv.locked_qty == 30  # 锁定库存保留，等待复核


def test_review_requires_picked(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())
    with pytest.raises(BusinessError):
        outbound_service.review_outbound_order(db_session, order.id)
    outbound_service.pick_outbound_order(db_session, order.id)
    reviewed = outbound_service.review_outbound_order(db_session, order.id)
    assert reviewed.status == "REVIEWED"


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


def test_ship_leaves_locked_zero_and_ledger_reconciles(db_session):
    """发货后 locked 归零，账面库存守恒，流水前后值可对账。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    order = outbound_service.create_outbound_order(db_session, _make_req())
    outbound_service.pick_outbound_order(db_session, order.id)
    outbound_service.review_outbound_order(db_session, order.id)
    order = outbound_service.ship_outbound_order(db_session, order.id)

    assert order.status == "SHIPPED"
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 70
    assert inv.locked_qty == 0
    # 账面守恒：出库 30 后总库存 = 期初 100 - 30
    assert inv.available_qty + inv.locked_qty == 70

    # 流水对账：INBOUND(available 0→100) / PICK_LOCK(available 100→70) / OUTBOUND(locked 30→0)
    flows = {f.flow_type: f for f in db_session.query(InventoryFlow).all()}
    assert set(flows) == {"INBOUND", "PICK_LOCK", "OUTBOUND"}
    assert flows["INBOUND"].before_qty == 0 and flows["INBOUND"].after_qty == 100
    assert flows["PICK_LOCK"].before_qty == 100 and flows["PICK_LOCK"].after_qty == 70
    assert flows["OUTBOUND"].before_qty == 30 and flows["OUTBOUND"].after_qty == 0


def test_concurrent_pick_no_oversell(db_session):
    """并发防超卖：10 件库存、两单各拣 6 件 → 至多一单成功，账面不为负。

    验证 lock_stock 的双保险：
    1. 先 SUM 校验总量；
    2. 逐行「条件 UPDATE（available >= take 才生效）」+ 失败重读，并发下陈旧读
       无法覆盖他人已提交的扣减（SQLite 无行锁同样有效，PostgreSQL 另有 FOR UPDATE）。
    """
    _seed_stock(db_session, 1, "LOC-01", 10)
    o1 = outbound_service.create_outbound_order(db_session, _make_req(
        items=[OutboundItemRequest(productId=1, quantity=6, locationCode="LOC-01")]))
    o2 = outbound_service.create_outbound_order(db_session, _make_req(
        items=[OutboundItemRequest(productId=1, quantity=6, locationCode="LOC-01")]))

    engine = db_session.get_bind()
    outcomes: list[str] = []

    def _pick(order_id: int) -> None:
        session = Session(bind=engine)
        try:
            outbound_service.pick_outbound_order(session, order_id)
            outcomes.append("ok")
        except BusinessError as e:
            outcomes.append(f"rejected:{e.status}")  # 库存不足 409
        except OperationalError:
            outcomes.append("db-locked")             # SQLite 写锁冲突兜底
        finally:
            session.close()

    barrier = threading.Barrier(2)

    def _run(order_id: int) -> None:
        barrier.wait()
        _pick(order_id)

    threads = [threading.Thread(target=_run, args=(oid,)) for oid in (o1.id, o2.id)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("ok") <= 1  # 至多一单成功，杜绝超卖
    inv = db_session.query(Inventory).first()
    assert inv.locked_qty <= 6
    assert inv.available_qty >= 4
    assert inv.available_qty + inv.locked_qty == 10  # 账面总库存守恒
