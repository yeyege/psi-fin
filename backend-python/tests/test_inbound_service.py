"""入库单 Service 单元测试 — 状态机 PENDING → COMPLETED

对标领星WMS：
- 创建入库单（PENDING）不改变库存、不生成批次；
- 收货上架时才生成批次（批次号=单号-明细id）、累加库存并写流水。
"""
from datetime import datetime

import pytest

from app.common.errors import BusinessError
from app.models import Batch, InboundOrder, Inventory, InventoryFlow
from app.schemas import InboundOrderCreate, InboundItemRequest
from app.services import inbound_service


def _make_req(**kw) -> InboundOrderCreate:
    defaults = {
        "supplierName": "供应商X",
        "items": [InboundItemRequest(productId=1, quantity=100, locationCode="LOC-01")],
    }
    defaults.update(kw)
    return InboundOrderCreate(**defaults)


def test_create_inbound_order_pending_without_stock_change(db_session):
    """创建入库单：单号格式正确、状态 PENDING，且库存/批次/流水均为空。"""
    order = inbound_service.create_inbound_order(db_session, _make_req())

    today = datetime.now().strftime("%Y%m%d")
    assert order.order_no == f"IN-{today}-001"
    assert order.status == "PENDING"
    assert order.supplier_name == "供应商X"
    # 创建单不改变库存
    assert db_session.query(Inventory).count() == 0
    assert db_session.query(Batch).count() == 0
    assert db_session.query(InventoryFlow).count() == 0


def test_receive_inbound_adds_stock_batch_and_flow(db_session):
    """收货上架：生成批次、累加库存、写流水，状态置 COMPLETED。"""
    order = inbound_service.create_inbound_order(db_session, _make_req())
    order = inbound_service.receive_inbound_order(db_session, order.id)

    assert order.status == "COMPLETED"
    item = order.items[0]
    assert item.batch_id is not None
    batch = db_session.query(Batch).filter_by(id=item.batch_id).first()
    assert batch.batch_no == f"{order.order_no}-{item.id}"

    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 100
    assert inv.locked_qty == 0

    flows = db_session.query(InventoryFlow).filter_by(order_no=order.order_no).all()
    assert len(flows) == 1
    assert flows[0].flow_type == "INBOUND"
    assert flows[0].quantity == 100


def test_receive_twice_rejected(db_session):
    """重复收货应报错，且库存不重复累加。"""
    order = inbound_service.create_inbound_order(db_session, _make_req())
    inbound_service.receive_inbound_order(db_session, order.id)
    with pytest.raises(BusinessError):
        inbound_service.receive_inbound_order(db_session, order.id)
    inv = db_session.query(Inventory).first()
    assert inv.available_qty == 100


def test_create_inbound_invalid_product(db_session):
    with pytest.raises(BusinessError) as exc:
        inbound_service.create_inbound_order(
            db_session,
            _make_req(items=[InboundItemRequest(productId=999, quantity=1, locationCode="LOC-01")]),
        )
    assert exc.value.status == 404
    assert db_session.query(InboundOrder).count() == 0


def test_create_inbound_invalid_location(db_session):
    with pytest.raises(BusinessError) as exc:
        inbound_service.create_inbound_order(
            db_session,
            _make_req(items=[InboundItemRequest(productId=1, quantity=1, locationCode="NO-SUCH")]),
        )
    assert exc.value.status == 404
    assert db_session.query(InboundOrder).count() == 0


def test_order_no_increments_sequentially(db_session):
    o1 = inbound_service.create_inbound_order(db_session, _make_req())
    o2 = inbound_service.create_inbound_order(db_session, _make_req())
    assert o1.order_no.endswith("-001")
    assert o2.order_no.endswith("-002")
