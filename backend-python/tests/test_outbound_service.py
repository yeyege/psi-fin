"""出库单 Service 层单元测试 — 选做 A 并发安全验证

覆盖：
- 正常出库：库存正确扣减
- 超卖防护：库存不足抛 OutboundError(409)，且不产生部分扣减 / 单据
- 商品 / 库位不存在
- 同单据同(商品,库位)合并扣减
"""
import pytest

from app.models import Inventory, OutboundOrder
from app.schemas import OutboundOrderCreate, OutboundItemRequest
from app.services import outbound_service


def _seed_stock(db_session, pid, loc, qty):
    db_session.add(Inventory(product_id=pid, location_code=loc, quantity=qty))
    db_session.commit()


def test_create_outbound_order_deducts_stock(db_session):
    """正常出库：库存按数量扣减。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    req = OutboundOrderCreate(
        customerName="客户A",
        items=[OutboundItemRequest(productId=1, quantity=30, locationCode="LOC-01")],
    )
    order = outbound_service.create_outbound_order(db_session, req)
    assert order.status == "COMPLETED"

    inv = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    assert inv.quantity == 70  # 100 - 30


def test_outbound_oversell_prevented(db_session):
    """库存不足时拒绝出库(409)，且不创建单据、不产生部分扣减。"""
    _seed_stock(db_session, 1, "LOC-01", 5)
    req = OutboundOrderCreate(
        customerName="客户B",
        items=[OutboundItemRequest(productId=1, quantity=999, locationCode="LOC-01")],
    )
    with pytest.raises(outbound_service.OutboundError) as exc:
        outbound_service.create_outbound_order(db_session, req)
    assert exc.value.status == 409
    # 库存未被扣减（仍为 5）
    inv = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    assert inv.quantity == 5
    # 没有出库单被创建
    assert db_session.query(OutboundOrder).count() == 0


def test_outbound_missing_inventory_row_prevented(db_session):
    """库存行不存在时（等同于库存为 0）拒绝出库。"""
    req = OutboundOrderCreate(
        customerName="客户C",
        items=[OutboundItemRequest(productId=1, quantity=1, locationCode="LOC-01")],
    )
    with pytest.raises(outbound_service.OutboundError) as exc:
        outbound_service.create_outbound_order(db_session, req)
    assert exc.value.status == 409


def test_outbound_invalid_product(db_session):
    req = OutboundOrderCreate(
        customerName="客户D",
        items=[OutboundItemRequest(productId=999, quantity=1, locationCode="LOC-01")],
    )
    with pytest.raises(outbound_service.OutboundError) as exc:
        outbound_service.create_outbound_order(db_session, req)
    assert exc.value.status == 404


def test_outbound_aggregates_duplicate_items(db_session):
    """同单据同(商品,库位)合并后一次性扣减。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    req = OutboundOrderCreate(
        customerName="客户E",
        items=[
            OutboundItemRequest(productId=1, quantity=10, locationCode="LOC-01"),
            OutboundItemRequest(productId=1, quantity=20, locationCode="LOC-01"),
        ],
    )
    outbound_service.create_outbound_order(db_session, req)
    inv = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    assert inv.quantity == 70  # 100 - (10+20)


def test_outbound_atomic_rollback_on_partial_failure(db_session):
    """多明细中有一条库存不足时，整单回滚：已扣减的明细也应回滚。"""
    _seed_stock(db_session, 1, "LOC-01", 100)
    _seed_stock(db_session, 2, "LOC-02", 1)  # 第二条库存不足
    req = OutboundOrderCreate(
        customerName="客户F",
        items=[
            OutboundItemRequest(productId=1, quantity=50, locationCode="LOC-01"),
            OutboundItemRequest(productId=2, quantity=999, locationCode="LOC-02"),
        ],
    )
    with pytest.raises(outbound_service.OutboundError):
        outbound_service.create_outbound_order(db_session, req)

    # 第一条库存未被扣减（事务回滚）
    inv1 = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).first()
    assert inv1.quantity == 100
    assert db_session.query(OutboundOrder).count() == 0
