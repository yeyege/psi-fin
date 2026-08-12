"""库存服务 — 核心

设计原则（对标领星WMS）：
1. 所有库存变动必须通过本模块统一入口，强制写库存流水，保证全量可追溯；
2. 库存行维度为 (product_id, location_code, batch_id)，可用量(available) 与 锁定量(locked) 分离；
3. 扣减类操作支持跨批次（先扣早期批次），并做库存充足校验；
4. 出库锁定(lock) / 发货(ship) 为逐行原子操作，防止并发超卖。

注意：调用方必须处于数据库事务中（db.commit 由上层单据服务负责）。
"""
from sqlalchemy import func, or_, update
from sqlalchemy.orm import Session, joinedload

from app.common.errors import BusinessError
from app.models import Batch, Inventory, InventoryFlow, Location, Product, Warehouse

FLOW_TYPE_INBOUND = "INBOUND"        # 入库（+available）
FLOW_TYPE_OUTBOUND = "OUTBOUND"      # 出库发货（-locked）
FLOW_TYPE_PICK_LOCK = "PICK_LOCK"    # 拣货锁定（-available +locked）
FLOW_TYPE_MOVE_OUT = "MOVE_OUT"      # 移库出（-available）
FLOW_TYPE_MOVE_IN = "MOVE_IN"        # 移库入（+available）
FLOW_TYPE_ADJUST_IN = "ADJUST_IN"    # 调整盘盈（+available）
FLOW_TYPE_ADJUST_OUT = "ADJUST_OUT"  # 调整盘亏（-available）
FLOW_TYPE_RETURN_IN = "RETURN_IN"    # 退货收货（+available）

ORDER_TYPE_INBOUND = "INBOUND"
ORDER_TYPE_OUTBOUND = "OUTBOUND"
ORDER_TYPE_TRANSFER = "TRANSFER"
ORDER_TYPE_ADJUSTMENT = "ADJUSTMENT"
ORDER_TYPE_RETURN = "RETURN"


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
    """从 (product, location) 的库存中扣减可用量（跨批次，先扣早期批次）。

    返回 False 表示库存不足（不产生任何变更与流水）。
    注意：调用方事务中，若某次扣减跨多行，其中间写入会随上层回滚一起撤销。
    """
    rows = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.location_code == location_code,
            Inventory.available_qty > 0,
        )
        .order_by(Inventory.id.asc())
        .all()
    )
    total = sum(r.available_qty for r in rows)
    if total < quantity:
        return False

    remaining = quantity
    for row in rows:
        if remaining <= 0:
            break
        take = min(row.available_qty, remaining)
        before = row.available_qty
        row.available_qty -= take
        remaining -= take
        _add_flow(
            db, flow_type=flow_type, order_type=order_type, order_no=order_no,
            product_id=product_id, location_code=location_code, batch_id=row.batch_id,
            quantity=-take, before_qty=before, after_qty=row.available_qty,
            remark=remark,
        )
    return True


def lock_stock(db: Session, *, product_id: int, location_code: str, quantity: int,
               order_type: str, order_no: str, remark: str | None = None) -> bool:
    """拣货锁定：available -= q, locked += q（跨批次逐行，库存不足返回 False）。

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
    while remaining > 0:
        row = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == product_id,
                Inventory.location_code == location_code,
                Inventory.available_qty > 0,
            )
            .order_by(Inventory.id.asc())
            .with_for_update()  # 生产库(PostgreSQL)下加行锁；SQLite 忽略
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
    """出库发货：locked -= q（扣减已锁定库存），并写 OUTBOUND 流水。"""
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
    while remaining > 0:
        row = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == product_id,
                Inventory.location_code == location_code,
                Inventory.locked_qty > 0,
            )
            .order_by(Inventory.id.asc())
            .with_for_update()
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

    list_data = []
    for r in rows:
        item = {
            "productId": r.product_id,
            "productName": r.product_name,
            "sku": r.sku,
            "availableQty": r.available_qty,
            "lockedQty": r.locked_qty,
            "totalQty": (r.available_qty or 0) + (r.locked_qty or 0),
            "warehouseId": r.warehouse_id,
            "warehouseName": r.warehouse_name,
            "updatedAt": r.updated_at,
        }
        if view == "location":
            item["locationCode"] = r.location_code
            item["batchNo"] = r.batch_no
        list_data.append(item)

    return {"list": list_data, "total": total, "page": page, "pageSize": page_size}


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
    list_data = []
    for f in rows:
        list_data.append({
            "id": f.id,
            "flowType": f.flow_type,
            "orderType": f.order_type,
            "orderNo": f.order_no,
            "productId": f.product_id,
            "productName": f.product.name,
            "sku": f.product.sku,
            "locationCode": f.location_code,
            "batchNo": f.batch.batch_no if f.batch else None,
            "quantity": f.quantity,
            "beforeQty": f.before_qty,
            "afterQty": f.after_qty,
            "remark": f.remark,
            "createdAt": f.created_at,
        })
    return {"list": list_data, "total": total, "page": page, "pageSize": page_size}


def query_batches(db: Session, keyword: str | None = None,
                  page: int = 1, page_size: int = 20) -> dict:
    """批次列表。"""
    # joinedload 一次加载商品，避免拼响应时 N+1 逐行查库
    query = db.query(Batch).options(joinedload(Batch.product))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Batch.batch_no.like(like), Batch.product_id.in_(
                db.query(Product.id).filter(Product.name.like(like) | Product.sku.like(like))
            ))
        )
    total = query.count()
    rows = (
        query.order_by(Batch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    list_data = [
        {
            "id": b.id,
            "batchNo": b.batch_no,
            "productId": b.product_id,
            "productName": b.product.name if b.product else "",
            "sku": b.product.sku if b.product else "",
            "inboundDate": b.inbound_date,
            "manufactureDate": b.manufacture_date,
            "expiryDate": b.expiry_date,
        }
        for b in rows
    ]
    return {"list": list_data, "total": total, "page": page, "pageSize": page_size}
