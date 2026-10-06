"""库存服务 — 核心

设计原则（对标领星跨境仓储系统）：
1. 所有库存变动必须通过本模块统一入口，强制写库存流水，保证全量可追溯；
2. 库存行维度为 (product_id, location_code, batch_id)，可用量(available) 与 锁定量(locked) 分离；
3. 扣减类操作跨批次按效期优先选批次（FEFO，无有效期逐级退回生产日期、入库日期），并做库存充足校验；
4. 出库锁定(lock) / 发货(ship) 为逐行原子操作，防止并发超卖。

注意：调用方必须处于数据库事务中（db.commit 由上层单据服务负责）。
"""
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import case, func, or_, update
from sqlalchemy.orm import Session, joinedload

from app.common.errors import BusinessError
from app.common.pagination import page_result
from app.models import Batch, Inventory, InventoryFlow, Location, Product, Warehouse
from app.models.enums import FlowType, OrderType
from app.schemas import (
    BatchResponse, InventoryFlowResponse,
    InventoryProductViewResponse, InventoryRowResponse,
)

# 库存流水 / 来源单据类型：统一取自 enums（单一事实来源），保留模块级别名供其他 service 引用。
FLOW_TYPE_INBOUND = FlowType.INBOUND          # 入库（+available）
FLOW_TYPE_OUTBOUND = FlowType.OUTBOUND        # 出库发货（-locked）
FLOW_TYPE_PICK_LOCK = FlowType.PICK_LOCK      # 拣货锁定（-available +locked）
FLOW_TYPE_MOVE_OUT = FlowType.MOVE_OUT        # 移库出（-available）
FLOW_TYPE_MOVE_IN = FlowType.MOVE_IN          # 移库入（+available）
FLOW_TYPE_ADJUST_IN = FlowType.ADJUST_IN      # 调整盘盈（+available）
FLOW_TYPE_ADJUST_OUT = FlowType.ADJUST_OUT    # 调整盘亏（-available）
FLOW_TYPE_RETURN_IN = FlowType.RETURN_IN      # 退货收货（+available）

ORDER_TYPE_INBOUND = OrderType.INBOUND
ORDER_TYPE_OUTBOUND = OrderType.OUTBOUND
ORDER_TYPE_TRANSFER = OrderType.TRANSFER
ORDER_TYPE_ADJUSTMENT = OrderType.ADJUSTMENT
ORDER_TYPE_RETURN = OrderType.RETURN

# 条件 UPDATE 未命中（并发抢先扣走）后的最大重试次数。
# 每消耗一个库存行才前进一次，跨批次可能合法地循环很多次，所以只统计「冲突」次数；
# 连续几十次仍抢不到即病态竞争，此时抛错让调用方整单回滚（AGENTS.md §2），
# 而不是无界自旋拖死请求 —— SQLite 下 with_for_update() 被静默忽略（AGENTS.md §4），
# 两个事务互相把对方的条件打破是可能长期发生的，不是理论风险。
MAX_STOCK_CONFLICT_RETRY = 50


def _conflict_give_up(action: str, product_id: int, location_code: str) -> BusinessError:
    """三个扣减入口共用同一放弃口径与文案，免得三处各写一份而漂移。"""
    return BusinessError(
        f"{action}连续 {MAX_STOCK_CONFLICT_RETRY} 次遭遇并发冲突"
        f"(product={product_id}, location={location_code})，已放弃，请重试该单据",
        status=409,
    )


# 跨批次扣减的候选排序键（p0-2 design.md D1）：无批次行置后 → 有效期/生产日期/入库日期
# 逐列升序 → 同日期按建批先后与库存行主键稳定序。deduct_stock / lock_stock / ship_stock
# 三处共用同一份表达式：spec 把「发货与拣货保持同序」单列成一条 Requirement，
# 复制三份排序就是给漂移留口子。使用方需先 outerjoin Batch（后三个键取自批次表）。
FEFO_ORDER_KEYS = (
    # 键 1 不可省。ASC 下 NULL 的位置 SQLite 置前、PostgreSQL 置后，方言默认值相反；
    # 不显式钉住「无批次行排最后」，两种库会扣出两套批次顺序，而 SQLite 绿不会提示这一点。
    case((Batch.id.is_(None), 1), else_=0),
    # 键 2 一条 COALESCE 即覆盖 spec 的四级回退：有有效期按有效期，无则退回生产日期，再无退回入库日期。
    # 挂上批次的行 inbound_date 非空且 NOT NULL，所以此键为 NULL 的行只可能是无批次行 —— 已被键 1 置后，
    # 方言语义上的 NULL 排序差异因此影响不到结果。
    func.coalesce(Batch.expiry_date, Batch.manufacture_date, Batch.inbound_date),
    # 键 3/4：日期完全相同时按建批先后 + 库存行主键，延续旧「早期批次先扣」的 FIFO 语义，
    # 也使既有 test_deduct_stock_cross_batch_fifo（两批次同日建立）的原断言继续成立。
    Batch.id,
    Inventory.id,
)


# 批次生命周期阈值（临期 30 天 / 呆滞 180 天）。以模块常量落地、不落库，
# 可配置化按 p0-2 design.md 的安排留待后续。
EXPIRY_WARN_DAYS = 30
AGING_DAYS = 180

# 批次状态枚举：接口出参用英文枚举，展示文案由前端映射中文（p0-2 D4）。
BATCH_STATUS_NORMAL = "NORMAL"
BATCH_STATUS_EXPIRING = "EXPIRING"
BATCH_STATUS_EXPIRED = "EXPIRED"
BATCH_STATUS_AGING = "AGING"
# 枚举集合单一来源：路由的 status 参数校验由它拼出，不在 HTTP 层另写一份四个魔串
BATCH_STATUSES = (BATCH_STATUS_NORMAL, BATCH_STATUS_EXPIRING,
                  BATCH_STATUS_EXPIRED, BATCH_STATUS_AGING)


class BatchLifecycle(NamedTuple):
    """batch_lifecycle 的返回值。

    用命名元组而非裸三元组：库存明细与批次列表两个查询点取值时不靠位置对齐。
    days_to_expiry 仅在批次设有有效期时非空。
    """
    status: str
    days_to_expiry: int | None
    age_days: int


def batch_lifecycle(batch: Batch, now: datetime | None = None) -> BatchLifecycle:
    """批次生命周期状态的单一实现点，供 query_inventory(location 视图) 与 query_batches 共用。

    口径（spec Requirement「库存库位明细返回批次效期与状态」）：
    - 已过有效期至 → EXPIRED；有效期至在未来 EXPIRY_WARN_DAYS 天（含）以内 → EXPIRING
    - 未设有效期 且 入库上架超过 AGING_DAYS 天 → AGING；其余 → NORMAL
    - 呆滞只对未设有效期的批次成立：已设有效期的老批次走有效期分支，两个状态互斥

    纯函数：只读 batch 的日期字段，不写回实体、不查库。口径集在一处是有意为之，
    前端各算一份必然漂移（p0-2 D3）。
    """
    today = (now or datetime.now()).date()
    age_days = (today - batch.inbound_date.date()).days

    if batch.expiry_date is None:
        return BatchLifecycle(
            status=BATCH_STATUS_AGING if age_days > AGING_DAYS else BATCH_STATUS_NORMAL,
            days_to_expiry=None,
            age_days=age_days,
        )

    days_to_expiry = (batch.expiry_date.date() - today).days
    if days_to_expiry < 0:
        status = BATCH_STATUS_EXPIRED
    elif days_to_expiry <= EXPIRY_WARN_DAYS:
        status = BATCH_STATUS_EXPIRING
    else:
        status = BATCH_STATUS_NORMAL
    return BatchLifecycle(status=status, days_to_expiry=days_to_expiry, age_days=age_days)


def _get_or_create_inventory(db: Session, product_id: int, location_code: str,
                             batch_id: int | None) -> Inventory:
    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
            Inventory.batch_id == batch_id,
        )
        .first()
    )
    if inv is None:
        inv = Inventory(
            product_id=product_id,
            location_code=location_code,
            batch_id=batch_id,
            available_qty=0,
            locked_qty=0,
        )
        db.add(inv)
        db.flush()
    return inv


def _add_flow(db: Session, *, flow_type: str, order_type: str, order_no: str,
              product_id: int, location_code: str | None, batch_id: int | None,
              quantity: int, before_qty: int | None, after_qty: int | None,
              remark: str | None = None) -> None:
    db.add(InventoryFlow(
        flow_type=flow_type,
        order_type=order_type,
        order_no=order_no,
        product_id=product_id,
        location_code=location_code,
        batch_id=batch_id,
        quantity=quantity,
        before_qty=before_qty,
        after_qty=after_qty,
        remark=remark,
    ))


def add_stock(db: Session, *, product_id: int, location_code: str, batch_id: int | None,
              quantity: int, flow_type: str, order_type: str, order_no: str,
              remark: str | None = None) -> Inventory:
    """增加指定库存行的可用量，并写流水（用于入库/移库入/盘盈）。"""
    inv = _get_or_create_inventory(db, product_id, location_code, batch_id)
    before = inv.available_qty
    inv.available_qty += quantity
    _add_flow(
        db, flow_type=flow_type, order_type=order_type, order_no=order_no,
        product_id=product_id, location_code=location_code, batch_id=batch_id,
        quantity=quantity, before_qty=before, after_qty=inv.available_qty,
        remark=remark,
    )
    return inv


def deduct_stock(db: Session, *, product_id: int, location_code: str, quantity: int,
                 flow_type: str, order_type: str, order_no: str,
                 remark: str | None = None) -> bool:
    """从 (product, location) 的库存中扣减可用量（跨批次按效期优先，见 FEFO_ORDER_KEYS）。

    返回 False 表示库存不足（不产生任何变更与流水）。
    与 lock_stock 一致使用「条件 UPDATE（available >= take 才生效）+ 失败重读重试」，
    并发下陈旧读无法覆盖他人已提交的扣减（SQLite 无行锁时尤为关键）。
    注意：调用方事务中，若某次扣减跨多行，其中间写入会随上层回滚一起撤销。
    """
    total = (
        db.query(func.sum(Inventory.available_qty))
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
        )
        .scalar()
        or 0
    )
    if total < quantity:
        return False

    remaining = quantity
    conflicts = 0
    while remaining > 0:
        row = (
            db.query(Inventory)
            .outerjoin(Batch, Inventory.batch_id == Batch.id)
            .filter(
                Inventory.product_id == product_id,
                Inventory.location_code == location_code,
                Inventory.available_qty > 0,
            )
            .order_by(*FEFO_ORDER_KEYS)
            # of=Inventory 是必须的，不是美化：排序键取自批次表就得 outerjoin Batch，
            # 而 PostgreSQL 禁止对 LEFT JOIN 可空侧加行锁（FOR UPDATE cannot be applied to
            # the nullable side of an outer join）。不带 of 在 PG 上直接报错，SQLite 忽略
            # FOR UPDATE 所以单测给不出任何信号（AGENTS.md §4）。方言差异必须记住：PG 渲染
            # `FOR UPDATE OF inventory`（只锁库存行）；而 SQLAlchemy 的 MySQL 方言会丢弃 `of`、
            # 退化为裸 `FOR UPDATE`（连批次侧一起锁）。后者只影响锁范围，不影响防超卖语义。
            # 实测记录见 p0-2 tasks 2.1 完成记录。
            .with_for_update(of=Inventory)
            .first()
        )
        if row is None:
            return False
        take = min(row.available_qty, remaining)
        before = row.available_qty
        result = db.execute(
            update(Inventory)
            .where(Inventory.id == row.id, Inventory.available_qty >= take)
            .values(available_qty=Inventory.available_qty - take)
        )
        if result.rowcount == 0:
            conflicts += 1
            if conflicts > MAX_STOCK_CONFLICT_RETRY:
                raise _conflict_give_up("库存扣减", product_id, location_code)
            continue  # 该行已被并发修改，重读最新状态再扣
        remaining -= take
        _add_flow(
            db, flow_type=flow_type, order_type=order_type, order_no=order_no,
            product_id=product_id, location_code=location_code, batch_id=row.batch_id,
            quantity=-take, before_qty=before, after_qty=row.available_qty - take,
            remark=remark,
        )
    return True


def lock_stock(db: Session, *, product_id: int, location_code: str, quantity: int,
               order_type: str, order_no: str, remark: str | None = None) -> bool:
    """拣货锁定：available -= q, locked += q（跨批次逐行按效期优先，库存不足返回 False）。

    防超卖双保险：
    1. 先 SUM 校验总量，不足直接返回 False 且无副作用（调用方可整体回滚）；
    2. 逐行用「条件 UPDATE（available >= take 才生效）」写入，并发下陈旧读无法
       覆盖他人已提交的扣减（SQLite 无行锁时尤为关键，PostgreSQL 另有 FOR UPDATE 行锁）。
    """
    total = (
        db.query(func.sum(Inventory.available_qty))
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
        )
        .scalar()
        or 0
    )
    if total < quantity:
        return False

    remaining = quantity
    conflicts = 0
    while remaining > 0:
        row = (
            db.query(Inventory)
            .outerjoin(Batch, Inventory.batch_id == Batch.id)
            .filter(
                Inventory.product_id == product_id,
                Inventory.location_code == location_code,
                Inventory.available_qty > 0,
            )
            .order_by(*FEFO_ORDER_KEYS)
            # of=Inventory 是必须的，不是美化：排序键取自批次表就得 outerjoin Batch，
            # 而 PostgreSQL 禁止对 LEFT JOIN 可空侧加行锁（FOR UPDATE cannot be applied to
            # the nullable side of an outer join）。不带 of 在 PG 上直接报错，SQLite 忽略
            # FOR UPDATE 所以单测给不出任何信号（AGENTS.md §4）。方言差异必须记住：PG 渲染
            # `FOR UPDATE OF inventory`（只锁库存行）；而 SQLAlchemy 的 MySQL 方言会丢弃 `of`、
            # 退化为裸 `FOR UPDATE`（连批次侧一起锁）。后者只影响锁范围，不影响防超卖语义。
            # 实测记录见 p0-2 tasks 2.1 完成记录。
            .with_for_update(of=Inventory)
            .first()
        )
        if row is None:
            return False
        take = min(row.available_qty, remaining)
        before = row.available_qty
        result = db.execute(
            update(Inventory)
            .where(Inventory.id == row.id, Inventory.available_qty >= take)
            .values(
                available_qty=Inventory.available_qty - take,
                locked_qty=Inventory.locked_qty + take,
            )
        )
        if result.rowcount == 0:
            conflicts += 1
            if conflicts > MAX_STOCK_CONFLICT_RETRY:
                raise _conflict_give_up("拣货锁定", product_id, location_code)
            continue  # 该行已被并发修改，重读最新状态再扣
        remaining -= take
        _add_flow(
            db, flow_type=FLOW_TYPE_PICK_LOCK, order_type=order_type, order_no=order_no,
            product_id=product_id, location_code=location_code, batch_id=row.batch_id,
            quantity=take, before_qty=before, after_qty=before - take,
            remark=remark,
        )
    return True


def ship_stock(db: Session, *, product_id: int, location_code: str, quantity: int,
               order_type: str, order_no: str, remark: str | None = None) -> bool:
    """出库发货：locked -= q（扣减已锁定库存），并写 OUTBOUND 流水。

    候选排序与 lock_stock 共用 FEFO_ORDER_KEYS，保证先锁定的批次先被发货消耗（spec
    Requirement「出库发货与拣货锁定保持同序」）；同序的回归断言由 p0-2 tasks 4.1 负责。
    """
    total = (
        db.query(func.sum(Inventory.locked_qty))
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
        )
        .scalar()
        or 0
    )
    if total < quantity:
        return False

    remaining = quantity
    conflicts = 0
    while remaining > 0:
        row = (
            db.query(Inventory)
            .outerjoin(Batch, Inventory.batch_id == Batch.id)
            .filter(
                Inventory.product_id == product_id,
                Inventory.location_code == location_code,
                Inventory.locked_qty > 0,
            )
            .order_by(*FEFO_ORDER_KEYS)
            .with_for_update(of=Inventory)  # 同 deduct_stock：PG 不允许锁 LEFT JOIN 可空侧
            .first()
        )
        if row is None:
            return False
        take = min(row.locked_qty, remaining)
        before = row.locked_qty
        result = db.execute(
            update(Inventory)
            .where(Inventory.id == row.id, Inventory.locked_qty >= take)
            .values(locked_qty=Inventory.locked_qty - take)
        )
        if result.rowcount == 0:
            conflicts += 1
            if conflicts > MAX_STOCK_CONFLICT_RETRY:
                raise _conflict_give_up("发货扣减", product_id, location_code)
            continue  # 该行已被并发修改，重读最新状态再扣
        remaining -= take
        _add_flow(
            db, flow_type=FLOW_TYPE_OUTBOUND, order_type=order_type, order_no=order_no,
            product_id=product_id, location_code=location_code, batch_id=row.batch_id,
            quantity=-take, before_qty=before, after_qty=before - take,
            remark=remark,
        )
    return True


# ==================== 查询 ====================

def _row_lifecycle_kwargs(r) -> dict:
    """从 location 视图的查询行得出三个生命周期字段，供响应构造使用。

    状态口径仍只存在于 `batch_lifecycle`（p0-2 D3）：这里只是把行上的批次日期装成一个
    游离 Batch 传给它，而不是在查询处重写一份 if/elif —— 两份口径必然漂移。
    用 `batch_inbound_date` 而非 `batch_no` 做判据：它在 Batch 上 NOT NULL，有批次必有值；
    未挂批次的库存行（盘盈/调整产生）则三个字段全返回 None，不得回 0 天或误标 NORMAL。
    """
    if r.batch_inbound_date is None:
        return {"days_to_expiry": None, "age_days": None, "batch_status": None}
    lifecycle = batch_lifecycle(Batch(
        inbound_date=r.batch_inbound_date,
        manufacture_date=r.batch_manufacture_date,
        expiry_date=r.batch_expiry_date,
    ))
    return {
        "days_to_expiry": lifecycle.days_to_expiry,
        "age_days": lifecycle.age_days,
        "batch_status": lifecycle.status,
    }


def query_inventory(
    db: Session,
    view: str = "location",  # product | location
    keyword: str | None = None,
    warehouse_id: int | None = None,
    batch_no: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """库存查询。

    - view=product  ：按 (商品, 仓库) 汇总可用/锁定
    - view=location ：按 (商品, 库位, 批次) 明细
    """
    base = (
        db.query(Inventory)
        .join(Product, Product.id == Inventory.product_id)
        .join(Location, Location.code == Inventory.location_code)
        .join(Warehouse, Warehouse.id == Location.warehouse_id)
    )
    if keyword:
        like = f"%{keyword}%"
        base = base.filter(or_(Product.name.like(like), Product.sku.like(like)))
    if warehouse_id is not None:
        base = base.filter(Location.warehouse_id == warehouse_id)
    if batch_no:
        base = base.join(Batch, Batch.id == Inventory.batch_id).filter(
            Batch.batch_no.like(f"%{batch_no}%")
        )

    if view == "product":
        query = (
            base.with_entities(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("sku"),
                Warehouse.id.label("warehouse_id"),
                Warehouse.name.label("warehouse_name"),
                func.sum(Inventory.available_qty).label("available_qty"),
                func.sum(Inventory.locked_qty).label("locked_qty"),
                func.max(Inventory.updated_at).label("updated_at"),
            )
            .group_by(Product.id, Warehouse.id)
        )
    else:
        query = (
            base.with_entities(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("sku"),
                Inventory.location_code.label("location_code"),
                Warehouse.id.label("warehouse_id"),
                Warehouse.name.label("warehouse_name"),
                Location.zone_id.label("zone_id"),
                Batch.batch_no.label("batch_no"),
                # 三个日期取出来才能算生命周期：同一个 outerjoin，不额外查库（避免 N+1）
                Batch.inbound_date.label("batch_inbound_date"),
                Batch.manufacture_date.label("batch_manufacture_date"),
                Batch.expiry_date.label("batch_expiry_date"),
                Inventory.available_qty.label("available_qty"),
                Inventory.locked_qty.label("locked_qty"),
                Inventory.updated_at.label("updated_at"),
            )
            .outerjoin(Batch, Batch.id == Inventory.batch_id)
            .order_by(Inventory.updated_at.desc(), Inventory.id.desc())
        )

    total = query.count()
    rows = (
        query.order_by(func.max(Inventory.updated_at).desc(), func.max(Inventory.id).desc())
        if view == "product"
        else query
    )
    rows = rows.offset((page - 1) * page_size).limit(page_size).all()

    if view == "product":
        list_data = [
            InventoryProductViewResponse(
                product_id=r.product_id, product_name=r.product_name, sku=r.sku,
                warehouse_id=r.warehouse_id, warehouse_name=r.warehouse_name,
                available_qty=r.available_qty, locked_qty=r.locked_qty,
                total_qty=(r.available_qty or 0) + (r.locked_qty or 0),
                updated_at=r.updated_at,
            )
            for r in rows
        ]
    else:
        list_data = [
            InventoryRowResponse(
                product_id=r.product_id, product_name=r.product_name, sku=r.sku,
                location_code=r.location_code,
                warehouse_id=r.warehouse_id, warehouse_name=r.warehouse_name,
                batch_no=r.batch_no,
                available_qty=r.available_qty, locked_qty=r.locked_qty,
                total_qty=(r.available_qty or 0) + (r.locked_qty or 0),
                updated_at=r.updated_at,
                manufacture_date=r.batch_manufacture_date,
                expiry_date=r.batch_expiry_date,
                **_row_lifecycle_kwargs(r),
            )
            for r in rows
        ]

    list_data = [m.model_dump(by_alias=True) for m in list_data]
    return page_result(list_data, total, page, page_size)


def query_flows(
    db: Session,
    order_no: str | None = None,
    product_id: int | None = None,
    location_code: str | None = None,
    flow_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """库存流水查询（分页 + 过滤）。"""
    # joinedload 一次加载商品/批次，避免拼响应时 N+1 逐行查库
    query = (
        db.query(InventoryFlow)
        .join(Product, Product.id == InventoryFlow.product_id)
        .options(
            joinedload(InventoryFlow.product),
            joinedload(InventoryFlow.batch),
        )
    )
    if order_no:
        query = query.filter(InventoryFlow.order_no.like(f"%{order_no}%"))
    if product_id is not None:
        query = query.filter(InventoryFlow.product_id == product_id)
    if location_code:
        query = query.filter(InventoryFlow.location_code == location_code)
    if flow_type:
        query = query.filter(InventoryFlow.flow_type == flow_type)

    total = query.count()
    rows = (
        query.order_by(InventoryFlow.created_at.desc(), InventoryFlow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    list_data = [
        InventoryFlowResponse(
            id=f.id, flow_type=f.flow_type, order_type=f.order_type, order_no=f.order_no,
            product_id=f.product_id,
            product_name=f.product.name if f.product else "",
            sku=f.product.sku if f.product else "",
            location_code=f.location_code,
            batch_no=f.batch.batch_no if f.batch else None,
            quantity=f.quantity, before_qty=f.before_qty, after_qty=f.after_qty,
            remark=f.remark, created_at=f.created_at,
        )
        for f in rows
    ]
    return page_result([m.model_dump(by_alias=True) for m in list_data], total, page, page_size)


def _batch_row(b: Batch) -> dict:
    """批次列表的单行响应；库龄与状态统一由 `batch_lifecycle` 算（p0-2 D3）。"""
    lifecycle = batch_lifecycle(b)
    return BatchResponse(
        id=b.id, batch_no=b.batch_no, product_id=b.product_id,
        product_name=b.product.name if b.product else "",
        sku=b.product.sku if b.product else "",
        inbound_date=b.inbound_date,
        manufacture_date=b.manufacture_date, expiry_date=b.expiry_date,
        age_days=lifecycle.age_days, batch_status=lifecycle.status,
    ).model_dump(by_alias=True)


def query_batches(db: Session, keyword: str | None = None, status: str | None = None,
                  page: int = 1, page_size: int = 20) -> dict:
    """批次列表：每行带库龄与批次状态，可按状态筛选（p0-2 tasks 3.2）。

    状态是派生值、不入库，口径只存在于 `batch_lifecycle` 一处，所以带 status 时不能改写成
    SQL WHERE + CASE：那等于把同一段判定复制成第二份，而 spec 明确要求批次列表与库位明细
    两处状态口径一致，漂移正好发生在这类「看起来等价」的复制上。
    代价：筛选时先取全部匹配 keyword 的行算完状态再分页。当前批次量级可控（演示数据约千行）；
    真实量级上去后的正解是把口径做成单一 SQL 表达式让两处共用，而不是各写一份。
    缺省（不带 status）仍走 SQL 分页，不给既有路径加负担；total 返回筛选后的条数，
    否则前端分页会算出不存在的尾页。
    """
    # joinedload 一次加载商品，避免拼响应时 N+1 逐行查库
    query = db.query(Batch).options(joinedload(Batch.product))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Batch.batch_no.like(like), Batch.product_id.in_(
                db.query(Product.id).filter(Product.name.like(like) | Product.sku.like(like))
            ))
        )

    if status is None:
        total = query.count()
        rows = (
            query.order_by(Batch.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        list_data = [_batch_row(b) for b in rows]
    else:
        computed = [
            _batch_row(b)
            for b in query.order_by(Batch.created_at.desc()).all()
        ]
        matched = [row for row in computed if row["batchStatus"] == status]
        total = len(matched)
        list_data = matched[(page - 1) * page_size: page * page_size]

    return page_result(list_data, total, page, page_size)
