"""批次效期测试（openspec change `p0-2-strict-fifo-expiry` tasks 1.1 / 2.2）

覆盖 spec: specs/inventory/batch-expiry/spec.md 两条 Requirement：

一、「库存库位明细返回批次效期与状态」的状态口径（`batch_lifecycle` 纯函数，不需要 DB）：
- 已过有效期至 → 已过期；有效期至在未来 30 天（含）以内 → 临期
- **未设有效期**且入库上架超过 180 天 → 呆滞；其余 → 正常
- 关键约束：呆滞只对未设有效期的批次成立，已设有效期的老批次即便库龄超 180 天也不标呆滞
- 日期为空时对应字段返回 None（距到期天数依赖有效期）

二、「扣减批次按效期优先顺序选择」（tasks 2.2，打 `deduct_stock` 这个已有 seam）：
- 有效期升序 → 生产日期升序 → 入库日期升序 → 稳定序 的四级回退链
- 未挂批次的库存行最后被扣减

三条扣减用例都刻意把「建库存行的先后」与「应扣的先后」做成相反：若实现仍按
`Inventory.id` 排序，结果必然与断言相反，用例才会红。反过来插就能防住假绿。
"""
from datetime import datetime, timedelta

from sqlalchemy import func

from app.models import Batch, Inventory, InventoryFlow
from app.services import inventory_service


def _batch(expires_in=None, inbound_days_ago=None, manufactured_days_ago=None):
    """构造未入库的瞬时 Batch（纯函数不依赖 DB），按相对天数生成日期。"""
    now = datetime.now()
    return Batch(
        batch_no="B-TEST",
        product_id=1,
        inbound_date=now - timedelta(days=inbound_days_ago if inbound_days_ago is not None else 0),
        manufacture_date=(now - timedelta(days=manufactured_days_ago))
                         if manufactured_days_ago is not None else None,
        expiry_date=(now + timedelta(days=expires_in)) if expires_in is not None else None,
    )


def test_batch_status_calculations():
    """spec 四条口径逐一断言，含 30 天与 180 天的边界归属。"""
    # 已过期：有效期至早于今天
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=-1))
    assert lifecycle.status == inventory_service.BATCH_STATUS_EXPIRED
    assert lifecycle.days_to_expiry == -1

    # 临期上界：有效期至正好 30 天后（spec 写「30 天（含）以内」）
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=inventory_service.EXPIRY_WARN_DAYS))
    assert lifecycle.status == inventory_service.BATCH_STATUS_EXPIRING
    assert lifecycle.days_to_expiry == inventory_service.EXPIRY_WARN_DAYS

    # 临期典型值：10 天后到期，spec 的 Scenario 用例
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=10))
    assert lifecycle.status == inventory_service.BATCH_STATUS_EXPIRING
    assert lifecycle.days_to_expiry == 10

    # 有效期至边界：正好今天尚未过期，仍属临期而非已过期
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=0))
    assert lifecycle.status == inventory_service.BATCH_STATUS_EXPIRING
    assert lifecycle.days_to_expiry == 0

    # 正常：有效期远在 30 天之外
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=60))
    assert lifecycle.status == inventory_service.BATCH_STATUS_NORMAL
    assert lifecycle.days_to_expiry == 60

    # 呆滞下界：未设有效期且入库超过 180 天
    lifecycle = inventory_service.batch_lifecycle(
        _batch(expires_in=None, inbound_days_ago=inventory_service.AGING_DAYS + 1))
    assert lifecycle.status == inventory_service.BATCH_STATUS_AGING
    assert lifecycle.days_to_expiry is None
    assert lifecycle.age_days == inventory_service.AGING_DAYS + 1

    # 呆滞边界：恰好 180 天属「未超过」，仍为正常
    lifecycle = inventory_service.batch_lifecycle(
        _batch(expires_in=None, inbound_days_ago=inventory_service.AGING_DAYS))
    assert lifecycle.status == inventory_service.BATCH_STATUS_NORMAL
    assert lifecycle.age_days == inventory_service.AGING_DAYS

    # 未设有效期且库龄浅：正常，距到期天数为空
    lifecycle = inventory_service.batch_lifecycle(_batch(expires_in=None, inbound_days_ago=5))
    assert lifecycle.status == inventory_service.BATCH_STATUS_NORMAL
    assert lifecycle.days_to_expiry is None
    assert lifecycle.age_days == 5


def test_aging_applies_only_to_batches_without_expiry_date():
    """spec 口径是「未设有效期但入库超过 180 天为呆滞」。

    已设有效期的老批次走有效期分支，不因库龄被标呆滞 —— 两种状态在此互斥，
    否则一个 200 天前入库、还有 10 天到期的批次会被同时判成临期与呆滞。
    """
    lifecycle = inventory_service.batch_lifecycle(
        _batch(expires_in=10, inbound_days_ago=200))

    assert lifecycle.status == inventory_service.BATCH_STATUS_EXPIRING
    assert lifecycle.age_days == 200          # 库龄照常返回，只是不参与状态判定


def test_pure_function_does_not_mutate_batch():
    """纯函数：读日期字段、不写回 Batch，避免调用方拿到被污染的实体。"""
    batch = _batch(expires_in=10, inbound_days_ago=200)
    before = (batch.inbound_date, batch.manufacture_date, batch.expiry_date)

    inventory_service.batch_lifecycle(batch)

    assert (batch.inbound_date, batch.manufacture_date, batch.expiry_date) == before


# ============ 扣减候选排序：效期优先（tasks 2.2） ============

LOCATION = "LOC-01"


def _inbound(db, *, batch_no: str, qty: int, expiry_in=None,
             manufactured_ago=None, inbound_ago=0) -> Inventory:
    """建一个批次并入库若干件到 LOC-01，返回那条库存行。

    日期全部按相对今天的天数生成，断言因此不受运行日期影响。
    """
    now = datetime.now()
    batch = Batch(
        batch_no=batch_no,
        product_id=1,
        inbound_date=now - timedelta(days=inbound_ago),
        manufacture_date=(now - timedelta(days=manufactured_ago))
                         if manufactured_ago is not None else None,
        expiry_date=(now + timedelta(days=expiry_in)) if expiry_in is not None else None,
    )
    db.add(batch)
    db.flush()
    return inventory_service.add_stock(
        db, product_id=1, location_code=LOCATION, batch_id=batch.id, quantity=qty,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no=f"T-IN-{batch_no}",
    )


def _deduct(db, quantity: int) -> bool:
    return inventory_service.deduct_stock(
        db, product_id=1, location_code=LOCATION, quantity=quantity,
        flow_type=inventory_service.FLOW_TYPE_MOVE_OUT,
        order_type=inventory_service.ORDER_TYPE_TRANSFER, order_no="T-FEFO",
    )


def test_earlier_expiry_deducted_first_even_when_later_in_stock(db_session):
    """spec Scenario「有效期的先扣」：先到期先出，压过入库先后。

    批次 A 先入库(10 天前)但 30 天后才到期，批次 B 后入库(1 天前)却 5 天后到期；
    B 的库存行也刻意晚于 A 建立，因此「按 Inventory.id」的旧排序会先扣 A。
    """
    row_a = _inbound(db_session, batch_no="FEFO-A", qty=30, expiry_in=30, inbound_ago=10)
    row_b = _inbound(db_session, batch_no="FEFO-B", qty=20, expiry_in=5, inbound_ago=1)

    assert _deduct(db_session, 30) is True
    db_session.refresh(row_b)
    db_session.refresh(row_a)
    assert row_b.available_qty == 0     # B 先到期 → 先扣尽
    assert row_a.available_qty == 20    # 不足部分才落到 A


def test_no_expiry_falls_back_to_manufacture_date(db_session):
    """spec Scenario「无有效期退回生产日期」：都无有效期时按生产日期升序先出。

    D 先入库(10 天前)且库存行先建，C 后入库(1 天前)但生产日期早 40 天 →
    应扣 C；回退链若只看入库日期或行号都会先扣 D。
    """
    row_d = _inbound(db_session, batch_no="FEFO-D", qty=40,
                     manufactured_ago=20, inbound_ago=10)
    row_c = _inbound(db_session, batch_no="FEFO-C", qty=10,
                     manufactured_ago=60, inbound_ago=1)

    assert _deduct(db_session, 10) is True
    db_session.refresh(row_c)
    db_session.refresh(row_d)
    assert row_c.available_qty == 0     # 生产日期更早的先扣尽
    assert row_d.available_qty == 40    # 生产日期更晚的分毫未动


def test_inventory_row_without_batch_is_deducted_last(db_session):
    """spec Scenario「无批次行最后扣」：先扣尽挂批次行，再扣 batch 为空的行为主。"""
    loose = inventory_service.add_stock(
        db_session, product_id=1, location_code=LOCATION, batch_id=None, quantity=50,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="T-IN-LOOSE",
    )
    batched = _inbound(db_session, batch_no="FEFO-E", qty=10, expiry_in=100)

    assert _deduct(db_session, 40) is True
    db_session.refresh(batched)
    db_session.refresh(loose)
    assert batched.available_qty == 0   # 挂批次行先扣尽
    assert loose.available_qty == 20    # 差额才由无批次行承担

    # spec Scenario「库存不足无副作用」：失败既不得改变数量，也不得留下流水。
    # 只数 Inventory 行数会是恒真断言 —— 扣减失败从不增删库存行；必须盯数量与流水。
    flows_before = db_session.query(InventoryFlow).count()
    qty_before = _available_total(db_session)

    assert _deduct(db_session, 999) is False

    assert _available_total(db_session) == qty_before
    assert db_session.query(InventoryFlow).count() == flows_before


def _available_total(db) -> int:
    """该商品在本库位的可用量合计，供「无副作用」断言拿基准值。"""
    return db.query(func.coalesce(func.sum(Inventory.available_qty), 0)).filter(
        Inventory.product_id == 1, Inventory.location_code == LOCATION
    ).scalar()


# ============ 查询接口返回生命周期字段与状态筛选（tasks 3.1 / 3.2） ============

def _row_by_batch(rows, batch_no_prefix: str | None) -> dict:
    """按批次号前缀取 location 视图里的一行；传 None 则取无批次的那一行。"""
    for row in rows:
        if batch_no_prefix is None:
            if row["batchNo"] is None:
                return row
        elif row["batchNo"] and row["batchNo"].startswith(batch_no_prefix):
            return row
    raise AssertionError(f"未找到批次 {batch_no_prefix!r} 的库存行")


def test_location_view_returns_batch_lifecycle_fields(db_session):
    """spec Requirement「库存库位明细返回批次效期与状态」。

    状态必须由 `batch_lifecycle` 这一个实现点算出，不得在查询处重写口径。
    """
    _inbound(db_session, batch_no="Q-EXPIRING", qty=5, expiry_in=10, inbound_ago=5)
    _inbound(db_session, batch_no="Q-AGING", qty=5, inbound_ago=200)
    inventory_service.add_stock(
        db_session, product_id=1, location_code=LOCATION, batch_id=None, quantity=5,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="T-IN-Q-LOOSE",
    )

    rows = inventory_service.query_inventory(db_session, view="location")["list"]

    expiring = _row_by_batch(rows, "Q-EXPIRING")
    assert expiring["batchStatus"] == "EXPIRING"
    assert expiring["daysToExpiry"] == 10
    assert expiring["ageDays"] == 5
    assert expiring["expiryDate"] is not None

    aging = _row_by_batch(rows, "Q-AGING")
    assert aging["batchStatus"] == "AGING"
    assert aging["daysToExpiry"] is None      # 未设有效期，距到期天数置空
    assert aging["ageDays"] == 200

    # 无批次行没有任何批次日期可算，五个派生字段全空而不是报 0 或乱标状态
    loose = _row_by_batch(rows, None)
    assert loose["batchStatus"] is None
    assert loose["daysToExpiry"] is None
    assert loose["ageDays"] is None
    assert loose["expiryDate"] is None
    assert loose["manufactureDate"] is None


def test_product_view_untouched_by_location_lifecycle_fields(db_session):
    """只给 location 明细加字段；product 汇总视图跨批次聚合，批次状态无意义，不得出现该列。"""
    _inbound(db_session, batch_no="Q-SUM", qty=5, expiry_in=10)

    rows = inventory_service.query_inventory(db_session, view="product")["list"]

    assert rows and all("batchStatus" not in row for row in rows)
    assert rows[0]["availableQty"] == 5


def test_query_batches_returns_lifecycle_fields(db_session):
    """spec Requirement「批次列表返回生命周期字段」：每行带 ageDays 与 batchStatus。"""
    _inbound(db_session, batch_no="L-NORMAL", qty=3, expiry_in=90, inbound_ago=2)
    _inbound(db_session, batch_no="L-EXPIRING", qty=3, expiry_in=5, inbound_ago=40)

    data = inventory_service.query_batches(db_session)

    by_no = {row["batchNo"]: row for row in data["list"]}
    assert by_no["L-NORMAL"]["batchStatus"] == "NORMAL"
    assert by_no["L-NORMAL"]["ageDays"] == 2
    assert by_no["L-EXPIRING"]["batchStatus"] == "EXPIRING"
    assert by_no["L-EXPIRING"]["ageDays"] == 40


def test_query_batches_status_filter_keeps_pagination_consistent(db_session):
    """spec Scenario「批次列表按状态筛选」与「缺省返回全部」。

    total 必须是筛选后的条数而不是全表条数，否则前端分页会算出空尾页。
    """
    _inbound(db_session, batch_no="F-EXP", qty=1, expiry_in=3)
    _inbound(db_session, batch_no="F-AGING", qty=1, inbound_ago=300)
    _inbound(db_session, batch_no="F-NORMAL", qty=1, expiry_in=400)

    all_data = inventory_service.query_batches(db_session)
    assert all_data["total"] == 3
    assert {row["batchStatus"] for row in all_data["list"]} == {"EXPIRING", "AGING", "NORMAL"}

    filtered = inventory_service.query_batches(db_session, status="AGING")
    assert filtered["total"] == 1
    assert [row["batchNo"] for row in filtered["list"]] == ["F-AGING"]
    assert all(row["batchStatus"] == "AGING" for row in filtered["list"])
