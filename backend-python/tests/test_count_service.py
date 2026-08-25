"""盘点闭环 Service 单元测试

对标领星 WMS 盘点：
- 创建盘点单：按 库位/库区/商品/全部 快照账面库存（可用+锁定合计）；
- 录入实盘数量（可多次覆盖，完成后不可再录）；
- 完成盘点：差异行自动生成盘盈/盘亏调整单 + 流水留痕，盘亏不足整单回滚；
- 准确率指标：库存准确率（SKU×库位 账实相符）、库位准确率、差异总量。
"""
from datetime import datetime

import pytest

from app.common.errors import BusinessError
from app.models import (
    Batch, CycleCount, Inventory, InventoryFlow, StockAdjustment,
)
from app.schemas import CountCreate, CountSubmit, CountSubmitItem
from app.services import count_service, inventory_service


def _seed_stock(db, pid: int, loc: str, qty: int, batch_no: str | None = None):
    b = Batch(batch_no=batch_no or f"B-{pid}-{loc}-{qty}", product_id=pid,
              inbound_date=datetime.now())
    db.add(b)
    db.flush()
    inventory_service.add_stock(
        db, product_id=pid, location_code=loc, batch_id=b.id, quantity=qty,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="SEED",
    )
    db.commit()
    return b


def _count_req(scope_type: str, scope_value: str | None = None,
               **kw) -> CountCreate:
    defaults = {"scopeType": scope_type, "scopeValue": scope_value}
    defaults.update(kw)
    return CountCreate(**defaults)


def _submit(count, *pairs) -> CountSubmit:
    """按 (product_id, location_code, counted_qty) 三元组构造提交请求。"""
    item_map = {(it.product_id, it.location_code): it for it in count.items}
    return CountSubmit(items=[
        CountSubmitItem(itemId=item_map[(pid, loc)].id, countedQty=qty)
        for pid, loc, qty in pairs
    ])


# ============ 创建盘点单 ============

def test_create_count_by_location_snapshots(db_session):
    _seed_stock(db_session, 1, "LOC-01", 30)
    _seed_stock(db_session, 2, "LOC-02", 20)
    count = count_service.create_count_order(
        db_session, _count_req("LOCATION", "LOC-01"))

    assert count.status == "PENDING"
    assert count.count_no.startswith("CC-")
    assert len(count.items) == 1
    it = count.items[0]
    assert it.product_id == 1 and it.location_code == "LOC-01"
    assert it.system_qty == 30 and it.counted_qty is None
    # 创建盘点单不改库存
    assert db_session.query(InventoryFlow).count() == 2


def test_create_count_by_zone(db_session):
    # LOC-01/LOC-02 同属 zone 1，库存各 10
    _seed_stock(db_session, 1, "LOC-01", 10)
    _seed_stock(db_session, 1, "LOC-02", 10)
    count = count_service.create_count_order(
        db_session, _count_req("ZONE", "1"))

    assert len(count.items) == 2
    assert {it.location_code for it in count.items} == {"LOC-01", "LOC-02"}


def test_create_count_by_product(db_session):
    _seed_stock(db_session, 1, "LOC-01", 5)
    _seed_stock(db_session, 2, "LOC-02", 8)
    count = count_service.create_count_order(
        db_session, _count_req("PRODUCT", "1"))

    assert len(count.items) == 1
    assert count.items[0].product_id == 1
    assert count.items[0].system_qty == 5


def test_create_count_all_aggregates_multi_batch(db_session):
    _seed_stock(db_session, 1, "LOC-01", 40, batch_no="B1")
    _seed_stock(db_session, 1, "LOC-01", 60, batch_no="B2")
    count = count_service.create_count_order(db_session, _count_req("ALL"))

    # 同商品同库位多批次按 (商品, 库位) 聚合快照
    assert len(count.items) == 1
    assert count.items[0].system_qty == 100


def test_create_count_invalid_scope_404(db_session):
    with pytest.raises(BusinessError) as exc:
        count_service.create_count_order(db_session, _count_req("LOCATION", "NO-LOC"))
    assert exc.value.status == 404

    with pytest.raises(BusinessError) as exc:
        count_service.create_count_order(db_session, _count_req("ZONE", "999"))
    assert exc.value.status == 404


def test_create_count_missing_scope_value_rejected(db_session):
    with pytest.raises(BusinessError) as exc:
        count_service.create_count_order(db_session, _count_req("PRODUCT"))
    assert exc.value.status == 400


def test_count_no_increments(db_session):
    c1 = count_service.create_count_order(db_session, _count_req("ALL"))
    c2 = count_service.create_count_order(db_session, _count_req("ALL"))
    assert c2.count_no > c1.count_no


# ============ 录入实盘 ============

def test_submit_count_items(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))

    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 12)).items)
    assert count.items[0].counted_qty == 12

    # 可再次覆盖
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 9)).items)
    assert count.items[0].counted_qty == 9


def test_submit_after_completed_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 10)).items)
    count_service.complete_count(db_session, count.id)

    with pytest.raises(BusinessError):
        count_service.submit_count_items(
            db_session, count.id, _submit(count, (1, "LOC-01", 12)).items)


# ============ 完成盘点 ============

def test_complete_with_unrecorded_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("ALL"))
    with pytest.raises(BusinessError) as exc:
        count_service.complete_count(db_session, count.id)
    assert "未录入实盘数量" in exc.value.message
    assert db_session.query(CycleCount).first().status == "PENDING"


def test_complete_no_diff_no_adjustment(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 10)).items)
    count = count_service.complete_count(db_session, count.id)

    assert count.status == "COMPLETED"
    assert db_session.query(StockAdjustment).count() == 0


def test_complete_generates_gain_adjustment_and_flow(db_session):
    _seed_stock(db_session, 1, "LOC-01", 30)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 45)).items)
    count = count_service.complete_count(db_session, count.id)

    adj = db_session.query(StockAdjustment).first()
    assert adj is not None
    assert adj.count_id == count.id
    assert f"{count.count_no}" in adj.remark
    assert adj.items[0].change_qty == 15

    rows = db_session.query(Inventory).filter_by(product_id=1, location_code="LOC-01").all()
    assert sum(r.available_qty for r in rows) == 45
    flow = db_session.query(InventoryFlow).filter_by(flow_type="ADJUST_IN").first()
    assert flow is not None
    assert flow.order_no == adj.order_no
    assert count.count_no in (flow.remark or "")


def test_complete_generates_loss_adjustment(db_session):
    _seed_stock(db_session, 1, "LOC-01", 30)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 18)).items)
    count = count_service.complete_count(db_session, count.id)

    adj = db_session.query(StockAdjustment).first()
    assert adj.items[0].change_qty == -12
    rows = db_session.query(Inventory).filter_by(product_id=1, location_code="LOC-01").all()
    assert sum(r.available_qty for r in rows) == 18
    assert db_session.query(InventoryFlow).filter_by(flow_type="ADJUST_OUT").count() == 1


def test_complete_loss_insufficient_rollback(db_session):
    # 快照 10，随后并发扣减 8（剩 2），盘点按 0 实盘 → 盘亏 10 超出现有可用 → 回滚
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    inventory_service.deduct_stock(
        db_session, product_id=1, location_code="LOC-01", quantity=8,
        flow_type=inventory_service.FLOW_TYPE_ADJUST_OUT,
        order_type=inventory_service.ORDER_TYPE_ADJUSTMENT, order_no="EXTRA")
    db_session.commit()

    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 0)).items)
    with pytest.raises(BusinessError) as exc:
        count_service.complete_count(db_session, count.id)
    assert exc.value.status == 409

    # 整单回滚：无调整单、盘点单保持 PENDING、库存未被扣成负数
    assert db_session.query(StockAdjustment).count() == 0
    assert db_session.query(CycleCount).first().status == "PENDING"
    rows = db_session.query(Inventory).filter_by(product_id=1, location_code="LOC-01").all()
    assert sum(r.available_qty for r in rows) == 2


def test_complete_twice_rejected(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count = count_service.create_count_order(db_session, _count_req("LOCATION", "LOC-01"))
    count = count_service.submit_count_items(
        db_session, count.id, _submit(count, (1, "LOC-01", 10)).items)
    count_service.complete_count(db_session, count.id)

    with pytest.raises(BusinessError):
        count_service.complete_count(db_session, count.id)
    assert db_session.query(StockAdjustment).count() == 0


# ============ 准确率统计 ============

def test_stats_accuracy_rates(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    _seed_stock(db_session, 2, "LOC-02", 5)
    count = count_service.create_count_order(db_session, _count_req("ALL"))
    count = count_service.submit_count_items(
        db_session, count.id,
        _submit(count, (1, "LOC-01", 10), (2, "LOC-02", 8)).items)
    count = count_service.complete_count(db_session, count.id)

    resp = count_service._build_response(count)
    stats = resp["stats"]
    assert stats["totalItems"] == 2
    assert stats["accurateItems"] == 1
    assert stats["accuracyRate"] == 0.5          # 库存准确率
    assert stats["locationCount"] == 2
    assert stats["accurateLocationCount"] == 1
    assert stats["locationAccuracyRate"] == 0.5  # 库位准确率
    assert stats["totalDiffQty"] == 3            # 差异总量（|10-10| + |8-5|）


def test_stats_empty_count(db_session):
    count = count_service.create_count_order(db_session, _count_req("ALL"))
    resp = count_service._build_response(count)
    assert resp["stats"]["totalItems"] == 0
    assert resp["stats"]["accuracyRate"] is None


def test_list_counts(db_session):
    _seed_stock(db_session, 1, "LOC-01", 10)
    count_service.create_count_order(db_session, _count_req("ALL"))
    result = count_service.list_counts(db_session)
    assert result["total"] == 1
    assert result["list"][0]["countNo"].startswith("CC-")
    assert result["list"][0]["items"][0]["systemQty"] == 10
