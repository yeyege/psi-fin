"""入库单 Service 层单元测试 — 选做 B（必做：至少 2 个用例）

覆盖：
- 正常创建：单号格式、状态、库存累加（已有行 + 新建行）
- 异常：商品不存在 / 库位不存在
- 同单据同(商品,库位)合并累加
- 事务回滚：异常时库存不被部分更新
"""
from datetime import datetime

import pytest

from app.models import Inventory, InboundOrder
from app.schemas import InboundOrderCreate, InboundItemRequest
from app.services import inbound_service


def test_create_inbound_order_accumulates_inventory(db_session):
    """正常创建：单号格式正确、状态 COMPLETED、库存累加到已有行。"""
    # 先放一条已有库存
    db_session.add(Inventory(product_id=1, location_code="LOC-01", quantity=50))
    db_session.commit()

    req = InboundOrderCreate(
        supplierName="供应商X",
        items=[InboundItemRequest(productId=1, quantity=100, locationCode="LOC-01")],
    )
    order = inbound_service.create_inbound_order(db_session, req)

    # 单号格式 IN-YYYYMMDD-XXX
    today = datetime.now().strftime("%Y%m%d")
    assert order.order_no == f"IN-{today}-001"
    assert order.status == "COMPLETED"
    assert order.supplier_name == "供应商X"

    # 库存累加：50 + 100 = 150
    inv = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    assert inv.quantity == 150


def test_create_inbound_order_creates_new_inventory_row(db_session):
    """入库到没有库存的库位时，应新建库存行。"""
    req = InboundOrderCreate(
        supplierName="供应商Y",
        items=[InboundItemRequest(productId=2, quantity=30, locationCode="LOC-02")],
    )
    order = inbound_service.create_inbound_order(db_session, req)
    assert order.id is not None

    inv = db_session.query(Inventory).filter_by(
        product_id=2, location_code="LOC-02"
    ).first()
    assert inv is not None
    assert inv.quantity == 30


def test_create_inbound_order_aggregates_duplicate_items(db_session):
    """同一单据中同一(商品,库位)出现多次应合并累加，避免重复锁行。"""
    req = InboundOrderCreate(
        supplierName="供应商Z",
        items=[
            InboundItemRequest(productId=1, quantity=10, locationCode="LOC-01"),
            InboundItemRequest(productId=1, quantity=20, locationCode="LOC-01"),
        ],
    )
    inbound_service.create_inbound_order(db_session, req)

    inv = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    # 10 + 20 = 30，且只产生一条库存行
    assert inv.quantity == 30
    assert db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).count() == 1
    # 明细也按预期合并为一条
    order = db_session.query(InboundOrder).first()
    assert len(order.items) == 1
    assert order.items[0].quantity == 30


def test_create_inbound_order_invalid_product(db_session):
    """商品不存在时应抛 InboundError(404) 且不创建任何数据。"""
    req = InboundOrderCreate(
        supplierName="供应商E",
        items=[InboundItemRequest(productId=999, quantity=1, locationCode="LOC-01")],
    )
    with pytest.raises(inbound_service.InboundError) as exc:
        inbound_service.create_inbound_order(db_session, req)
    assert exc.value.status == 404
    # 事务回滚：不应有任何入库单
    assert db_session.query(InboundOrder).count() == 0


def test_create_inbound_order_invalid_location(db_session):
    """库位不存在时应抛 InboundError(404)。"""
    req = InboundOrderCreate(
        supplierName="供应商E",
        items=[InboundItemRequest(productId=1, quantity=1, locationCode="NO-SUCH-LOC")],
    )
    with pytest.raises(inbound_service.InboundError) as exc:
        inbound_service.create_inbound_order(db_session, req)
    assert exc.value.status == 404
    assert db_session.query(InboundOrder).count() == 0


def test_order_no_increments_sequentially(db_session):
    """同一天多次创建，单号序号应递增。"""
    req = InboundOrderCreate(
        supplierName="S",
        items=[InboundItemRequest(productId=1, quantity=1, locationCode="LOC-01")],
    )
    o1 = inbound_service.create_inbound_order(db_session, req)
    o2 = inbound_service.create_inbound_order(db_session, req)
    assert o1.order_no.endswith("-001")
    assert o2.order_no.endswith("-002")
