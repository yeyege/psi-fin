"""库内作业 Service 单元测试：移库 + 库存调整

对标领星WMS：
- 移库：源库位扣减（MOVE_OUT）+ 目标库位增加（MOVE_IN）双向流水，不足整单回滚；
- 调整：change_qty>0 盘盈(+)/ <0 盘亏(-)，均写流水，盘亏不足回滚。
"""
from datetime import datetime

import pytest

from app.common.errors import BusinessError
from app.models import Batch, Inventory, InventoryFlow, StockAdjustment, StockTransfer
from app.schemas import StockAdjustmentCreate, StockAdjustmentItemRequest
from app.schemas import StockTransferCreate, StockTransferItemRequest
from app.services import adjustment_service, inventory_service, transfer_service


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


def _transfer_req(**kw) -> StockTransferCreate:
    defaults = {
        "items": [StockTransferItemRequest(
            productId=1, quantity=30,
            fromLocationCode="LOC-01", toLocationCode="LOC-02",
        )],
    }
    defaults.update(kw)
    return StockTransferCreate(**defaults)


def test_transfer_moves_stock_with_bidirectional_flows(db_session):
    _seed_stock(db_session, 1, "LOC-01", 100)
    t = transfer_service.create_transfer(db_session, _transfer_req())

    assert t.status == "COMPLETED"
    inv_from = db_session.query(Inventory).filter_by(location_code="LOC-01").first()
    inv_to = db_session.query(Inventory).filter_by(location_code="LOC-02").first()
    assert inv_from.available_qty == 70
    assert inv_to.available_qty == 30

    types = {f.flow_type for f in db_session.query(InventoryFlow).all()}
    assert "MOVE_OUT" in types and "MOVE_IN" in types


def test_transfer_insufficient_rollback(db_session):
    _seed_stock(db_session, 1, "LOC-01", 5)
    with pytest.raises(BusinessError) as exc:
        transfer_service.create_transfer(
            db_session, _transfer_req(items=[StockTransferItemRequest(
                productId=1, quantity=10,
                fromLocationCode="LOC-01", toLocationCode="LOC-02",
            )])
        )
    assert exc.value.status == 409
    # 整单回滚：源库位未扣减、目标库位无库存行、无单据
    inv_from = db_session.query(Inventory).filter_by(location_code="LOC-01").first()
    assert inv_from.available_qty == 5
    assert db_session.query(Inventory).filter_by(location_code="LOC-02").first() is None
    assert db_session.query(StockTransfer).count() == 0


def _adjust_req(**kw) -> StockAdjustmentCreate:
    defaults = {
        "items": [StockAdjustmentItemRequest(productId=1, locationCode="LOC-01", changeQty=5)],
    }
    defaults.update(kw)
    return StockAdjustmentCreate(**defaults)


def test_adjustment_gain_adds_stock(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    adj = adjustment_service.create_adjustment(
        db_session, _adjust_req(items=[StockAdjustmentItemRequest(
            productId=1, locationCode="LOC-01", changeQty=5,
        )])
    )

    assert adj.status == "COMPLETED"
    # 盘盈不绑定批次，新增一行 batch_id=None；按(商品,库位)汇总应为 10+5
    rows = db_session.query(Inventory).filter_by(
        product_id=1, location_code="LOC-01"
    ).all()
    assert sum(r.available_qty for r in rows) == 15
    assert inventory_service.query_flows(db_session, flow_type="ADJUST_IN")["total"] == 1


def test_adjustment_loss_deducts_stock(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    adjustment_service.create_adjustment(
        db_session, _adjust_req(items=[StockAdjustmentItemRequest(
            productId=1, locationCode="LOC-01", changeQty=-3,
        )])
    )
    inv = db_session.query(Inventory).filter_by(location_code="LOC-01").first()
    assert inv.available_qty == 7
    assert inventory_service.query_flows(db_session, flow_type="ADJUST_OUT")["total"] == 1


def test_adjustment_loss_insufficient_rollback(db_session):
    _seed_stock(db_session, 1, "LOC-01", 2)
    with pytest.raises(BusinessError) as exc:
        adjustment_service.create_adjustment(
            db_session, _adjust_req(items=[StockAdjustmentItemRequest(
                productId=1, locationCode="LOC-01", changeQty=-5,
            )])
        )
    assert exc.value.status == 409
    inv = db_session.query(Inventory).filter_by(location_code="LOC-01").first()
    assert inv.available_qty == 2
    assert db_session.query(StockAdjustment).count() == 0
