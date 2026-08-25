"""盘点服务 — 库存准确率闭环（对标领星 WMS 盘点）

流程：创建盘点单（按库位/库区/商品/全部 快照账面库存）→ 录入实盘数量 → 完成盘点。
完成时：
- 差异行自动生成盘盈/盘亏调整单（ADJUST_IN / ADJUST_OUT 流水，备注记录来源盘点单）；
- 盘盈 add_stock 到无批次库存行；盘亏 deduct_stock 跨批次先扣早期批次；
- 完成后可统计「库存准确率 / 库位准确率」等信任指标。

状态机：PENDING(待盘点) → COMPLETED(已完成)
说明：账面数量为创建时快照（可用+锁定合计），差异 = 实盘 - 快照账面。
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.common import generate_order_no, BusinessError
from app.models import (
    CycleCount, CycleCountItem, StockAdjustment, StockAdjustmentItem,
    Product, Location, Zone, Inventory,
)
from app.services import inventory_service

STATUS_PENDING = "PENDING"
STATUS_COMPLETED = "COMPLETED"


def _validate_scope(db: Session, scope_type: str, scope_value: str | None) -> None:
    """校验盘点范围：范围值必填且对应基础数据存在（ALL 除外）。"""
    if scope_type == "ALL":
        return
    if not scope_value:
        raise BusinessError("请填写盘点范围值", 400)
    if scope_type == "LOCATION":
        if not db.query(Location).filter(Location.code == scope_value).first():
            raise BusinessError(f"库位不存在: {scope_value}", 404)
    elif scope_type == "ZONE":
        try:
            zone_id = int(scope_value)
        except ValueError:
            raise BusinessError("库区ID必须为数字", 400)
        if not db.query(Zone).filter(Zone.id == zone_id).first():
            raise BusinessError(f"库区不存在: {zone_id}", 404)
    elif scope_type == "PRODUCT":
        try:
            product_id = int(scope_value)
        except ValueError:
            raise BusinessError("商品ID必须为数字", 400)
        if not db.query(Product).filter(Product.id == product_id).first():
            raise BusinessError(f"商品不存在: {product_id}", 404)


def _scope_inventory_query(db: Session, scope_type: str, scope_value: str | None):
    """构造范围内库存行的查询（不限定批次，仅用于快照聚合）。"""
    query = db.query(Inventory)
    if scope_type == "LOCATION":
        query = query.filter(Inventory.location_code == scope_value)
    elif scope_type == "ZONE":
        query = query.join(Location, Location.code == Inventory.location_code).filter(
            Location.zone_id == int(scope_value))
    elif scope_type == "PRODUCT":
        query = query.filter(Inventory.product_id == int(scope_value))
    # ALL：全部库存
    return query


def _snapshot_items(db: Session, scope_type: str, scope_value: str | None) -> list[tuple[int, str, int]]:
    """按 (商品, 库位) 聚合范围内库存，快照账面数量（可用 + 锁定合计）。"""
    query = _scope_inventory_query(db, scope_type, scope_value)
    rows = (
        query.with_entities(
            Inventory.product_id,
            Inventory.location_code,
            func.sum(Inventory.available_qty + Inventory.locked_qty).label("total_qty"),
        )
        .group_by(Inventory.product_id, Inventory.location_code)
        .order_by(Inventory.location_code.asc(), Inventory.product_id.asc())
        .all()
    )
    return [(r.product_id, r.location_code, r.total_qty or 0) for r in rows]


def create_count_order(db: Session, data) -> CycleCount:
    """创建盘点单：快照范围内账面库存生成盘点明细（PENDING，不改库存）。"""
    _validate_scope(db, data.scope_type, data.scope_value)

    for attempt in range(5):
        count_no = generate_order_no(db, CycleCount, "CC", no_col="count_no")
        try:
            count = CycleCount(
                count_no=count_no,
                scope_type=data.scope_type,
                scope_value=data.scope_value if data.scope_type != "ALL" else None,
                status=STATUS_PENDING,
                remark=data.remark,
            )
            db.add(count)
            db.flush()
            for product_id, location_code, system_qty in _snapshot_items(
                    db, data.scope_type, data.scope_value):
                db.add(CycleCountItem(
                    count_id=count.id,
                    product_id=product_id,
                    location_code=location_code,
                    system_qty=system_qty,
                ))
            db.commit()
            db.refresh(count)
            return count
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("盘点单创建失败：单号冲突", 409)
    raise BusinessError("盘点单创建失败", 500)


def get_count_order(db: Session, count_id: int) -> CycleCount:
    count = (
        db.query(CycleCount)
        .options(
            joinedload(CycleCount.items).joinedload(CycleCountItem.product),
        )
        .filter(CycleCount.id == count_id)
        .first()
    )
    if not count:
        raise BusinessError("盘点单不存在", 404)
    return count


def submit_count_items(db: Session, count_id: int, items) -> CycleCount:
    """录入实盘数量（PENDING 状态，可多次提交覆盖）。"""
    count = get_count_order(db, count_id)
    if count.status != STATUS_PENDING:
        raise BusinessError(f"当前状态 {count.status} 不允许录入实盘数量")

    item_map = {it.id: it for it in count.items}
    for req in items:
        item = item_map.get(req.item_id)
        if item is None:
            raise BusinessError(f"盘点明细不存在: {req.item_id}", 404)
        item.counted_qty = req.counted_qty
    db.commit()
    db.refresh(count)
    return count


def _build_stats(count: CycleCount) -> dict:
    """盘点准确率指标：库存准确率（SKU×库位行账实相符）、库位准确率、差异总量。"""
    items = count.items
    total = len(items)
    if total == 0:
        return {
            "totalItems": 0, "accurateItems": 0, "accuracyRate": None,
            "locationCount": 0, "accurateLocationCount": 0,
            "locationAccuracyRate": None, "totalDiffQty": 0,
        }
    accurate = sum(
        1 for it in items
        if it.counted_qty is not None and it.counted_qty == it.system_qty
    )
    locs = {it.location_code for it in items}
    accurate_locs = {
        it.location_code for it in items
        if it.counted_qty is not None and it.counted_qty == it.system_qty
    }
    return {
        "totalItems": total,
        "accurateItems": accurate,
        "accuracyRate": round(accurate / total, 4),
        "locationCount": len(locs),
        "accurateLocationCount": len(accurate_locs),
        "locationAccuracyRate": round(len(accurate_locs) / len(locs), 4) if locs else None,
        "totalDiffQty": sum(
            abs(it.counted_qty - it.system_qty)
            for it in items if it.counted_qty is not None
        ),
    }


def _build_response(count: CycleCount, include_stats: bool = True) -> dict:
    return {
        "id": count.id,
        "countNo": count.count_no,
        "scopeType": count.scope_type,
        "scopeValue": count.scope_value,
        "status": count.status,
        "remark": count.remark,
        "items": [
            {
                "id": it.id,
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "sku": it.product.sku if it.product else "",
                "locationCode": it.location_code,
                "systemQty": it.system_qty,
                "countedQty": it.counted_qty,
                "diffQty": it.counted_qty - it.system_qty if it.counted_qty is not None else None,
            }
            for it in count.items
        ],
        "stats": _build_stats(count) if include_stats else None,
        "createdAt": count.created_at,
    }


def complete_count(db: Session, count_id: int) -> CycleCount:
    """完成盘点：PENDING → COMPLETED。

    校验全部明细已录入实盘数量；对差异行自动生成调整单并写流水；
    盘亏库存不足则整单回滚（盘点单保持 PENDING）。
    """
    count = get_count_order(db, count_id)
    if count.status != STATUS_PENDING:
        raise BusinessError(f"当前状态 {count.status} 不允许完成")

    unrecorded = [it for it in count.items if it.counted_qty is None]
    if unrecorded:
        raise BusinessError(f"还有 {len(unrecorded)} 行明细未录入实盘数量")

    try:
        # 汇总差异行（(商品, 库位) → 差异），同一商品库位只调整一次
        diff_map: dict[tuple[int, str], int] = {}
        for it in count.items:
            diff = it.counted_qty - it.system_qty
            if diff == 0:
                continue
            key = (it.product_id, it.location_code)
            diff_map[key] = diff_map.get(key, 0) + diff

        if diff_map:
            adjustment = StockAdjustment(
                order_no=generate_order_no(db, StockAdjustment, "ADJ"),
                status="COMPLETED",
                count_id=count.id,
                remark=f"盘点单 {count.count_no} 差异自动调整",
            )
            db.add(adjustment)
            db.flush()
            for (product_id, location_code), diff in diff_map.items():
                db.add(StockAdjustmentItem(
                    adjustment_id=adjustment.id,
                    product_id=product_id,
                    location_code=location_code,
                    change_qty=diff,
                ))
                if diff > 0:  # 盘盈
                    inventory_service.add_stock(
                        db, product_id=product_id, location_code=location_code,
                        batch_id=None, quantity=diff,
                        flow_type=inventory_service.FLOW_TYPE_ADJUST_IN,
                        order_type=inventory_service.ORDER_TYPE_ADJUSTMENT,
                        order_no=adjustment.order_no,
                        remark=f"盘点单 {count.count_no}",
                    )
                else:  # 盘亏（跨批次先扣早期批次，与 FIFO 一致）
                    ok = inventory_service.deduct_stock(
                        db, product_id=product_id, location_code=location_code,
                        quantity=-diff,
                        flow_type=inventory_service.FLOW_TYPE_ADJUST_OUT,
                        order_type=inventory_service.ORDER_TYPE_ADJUSTMENT,
                        order_no=adjustment.order_no,
                        remark=f"盘点单 {count.count_no}",
                    )
                    if not ok:
                        product = db.query(Product).filter(Product.id == product_id).first()
                        raise BusinessError(
                            f"盘亏失败：商品「{product.name if product else product_id}」"
                            f"在库位 {location_code} 可用库存不足 {-diff} 件",
                            status=409,
                        )

        count.status = STATUS_COMPLETED
        db.commit()
        db.refresh(count)
        return count
    except BusinessError:
        db.rollback()
        raise


def list_counts(db: Session, status: str | None = None,
                page: int = 1, page_size: int = 20) -> dict:
    query = db.query(CycleCount).options(
        joinedload(CycleCount.items).joinedload(CycleCountItem.product),
    )
    if status:
        query = query.filter(CycleCount.status == status)
    total = query.count()
    rows = (
        query.order_by(CycleCount.created_at.desc(), CycleCount.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_response(c) for c in rows], "total": total,
            "page": page, "pageSize": page_size}
