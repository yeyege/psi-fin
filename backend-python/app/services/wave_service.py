"""波次拣货服务 — 对标领星智能波次策略

流程：
1. create_wave：选中多张 PENDING 出库单 → 生成波次(WV)，每张出库单生成一张拣货单(PK)；
   拣货明细按 (商品, 库位) 聚合，并按「库位优先级降序」排序 —— 模拟 PDA 智能推荐库位与最优拣货路径。
2. pick_picking_order：执行拣货 → lock_stock 锁定库存（防超卖），出库单 PENDING → PICKED；
   波次内全部拣货单完成后波次自动 COMPLETED。

波次状态机：CREATED → PICKING(首单开始拣货) → COMPLETED(全部拣货完成)
拣货单状态机：CREATED → PICKED(库存已锁定)
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.common import generate_order_no, BusinessError
from app.models import (
    Wave, PickingOrder, PickingOrderItem,
    OutboundOrder, OutboundOrderItem, Product, Location,
)
from app.services import inventory_service, outbound_service

WAVE_STATUS_CREATED = "CREATED"
WAVE_STATUS_PICKING = "PICKING"
WAVE_STATUS_COMPLETED = "COMPLETED"

PICK_STATUS_CREATED = "CREATED"
PICK_STATUS_PICKED = "PICKED"


def _build_wave_response(wave: Wave) -> dict:
    return {
        "id": wave.id,
        "waveNo": wave.wave_no,
        "status": wave.status,
        "remark": wave.remark,
        "createdAt": wave.created_at,
        "pickingOrders": [_build_picking_response(p) for p in wave.picking_orders],
    }


def _build_picking_response(picking: PickingOrder) -> dict:
    return {
        "id": picking.id,
        "pickingNo": picking.picking_no,
        "waveId": picking.wave_id,
        "outboundOrderId": picking.outbound_order_id,
        "outboundOrderNo": picking.outbound_order.order_no if picking.outbound_order else "",
        "status": picking.status,
        "createdAt": picking.created_at,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "locationCode": it.location_code,
            }
            for it in sorted(picking.items, key=lambda i: (i.location_code, i.product_id))
        ],
    }


def create_wave(db: Session, outbound_order_ids: list[int], remark: str | None = None) -> Wave:
    """生成波次：聚合 PENDING 出库单，逐单生成拣货单（明细按库位优先级排序）。"""
    if not outbound_order_ids:
        raise BusinessError("请选择至少一张出库单")

    orders = (
        db.query(OutboundOrder)
        .filter(OutboundOrder.id.in_(outbound_order_ids))
        .options(joinedload(OutboundOrder.items).joinedload(OutboundOrderItem.product))
        .all()
    )
    found = {o.id for o in orders}
    missing = set(outbound_order_ids) - found
    if missing:
        raise BusinessError(f"出库单不存在: {sorted(missing)}", 404)
    for o in orders:
        if o.status != outbound_service.STATUS_PENDING:
            raise BusinessError(f"出库单 {o.order_no} 状态为 {o.status}，不可加入波次")
        if o.wave_id:
            raise BusinessError(f"出库单 {o.order_no} 已在波次中")

    # 库位优先级排序表：优先级高的库位先拣（模拟最优拣货路径）
    loc_priority = {
        l.code: l.priority
        for l in db.query(Location).all()
    }

    for attempt in range(5):
        wave_no = generate_order_no(db, Wave, "WV", no_col="wave_no")
        try:
            wave = Wave(wave_no=wave_no, status=WAVE_STATUS_CREATED, remark=remark)
            db.add(wave)
            db.flush()

            for order in orders:
                order.wave_id = wave.id
                picking = PickingOrder(
                    picking_no=generate_order_no(db, PickingOrder, "PK", no_col="picking_no"),
                    wave_id=wave.id,
                    outbound_order_id=order.id,
                    status=PICK_STATUS_CREATED,
                )
                db.add(picking)
                db.flush()

                # 聚合明细：同一(商品,库位)合并，并按库位优先级降序生成拣货项
                aggregated: dict[tuple[int, str], int] = {}
                for item in order.items:
                    key = (item.product_id, item.location_code)
                    aggregated[key] = aggregated.get(key, 0) + item.quantity
                for (pid, loc), qty in sorted(
                    aggregated.items(),
                    key=lambda kv: -loc_priority.get(kv[0][1], 0),
                ):
                    db.add(PickingOrderItem(
                        picking_order_id=picking.id,
                        product_id=pid,
                        quantity=qty,
                        location_code=loc,
                    ))

            db.commit()
            db.refresh(wave)
            return wave
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("波次创建失败：单号冲突", 409)
    raise BusinessError("波次创建失败", 500)


def get_wave(db: Session, wave_id: int) -> Wave:
    wave = db.query(Wave).filter(Wave.id == wave_id).first()
    if not wave:
        raise BusinessError("波次不存在", 404)
    return wave


def get_picking_order(db: Session, picking_order_id: int) -> PickingOrder:
    picking = (
        db.query(PickingOrder)
        .filter(PickingOrder.id == picking_order_id)
        .options(joinedload(PickingOrder.items).joinedload(PickingOrderItem.product))
        .first()
    )
    if not picking:
        raise BusinessError("拣货单不存在", 404)
    return picking


def pick_picking_order(db: Session, picking_order_id: int) -> PickingOrder:
    """执行拣货：锁定库存，出库单 PENDING → PICKED，拣货单 CREATED → PICKED。

    任一明细库存不足则整单回滚（不留半成品）。
    """
    picking = get_picking_order(db, picking_order_id)
    if picking.status != PICK_STATUS_CREATED:
        raise BusinessError(f"当前状态 {picking.status} 不允许拣货")

    try:
        for item in picking.items:
            ok = inventory_service.lock_stock(
                db, product_id=item.product_id, location_code=item.location_code,
                quantity=item.quantity,
                order_type=inventory_service.ORDER_TYPE_OUTBOUND,
                order_no=picking.picking_no,
            )
            if not ok:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                raise BusinessError(
                    f"库存不足：商品「{product.name if product else item.product_id}」"
                    f"在库位 {item.location_code} 可用库存不足 {item.quantity} 件",
                    status=409,
                )
    except BusinessError:
        db.rollback()
        raise

    picking.status = PICK_STATUS_PICKED
    # 出库单同步进入 PICKED（已在波次中，由拣货动作驱动状态）
    order = db.query(OutboundOrder).filter(OutboundOrder.id == picking.outbound_order_id).first()
    if order and order.status == outbound_service.STATUS_PENDING:
        order.status = outbound_service.STATUS_PICKED

    # 波次状态推进：首单拣货 → PICKING；全部完成 → COMPLETED
    wave = get_wave(db, picking.wave_id)
    if wave.status == WAVE_STATUS_CREATED:
        wave.status = WAVE_STATUS_PICKING
    all_done = all(p.status == PICK_STATUS_PICKED for p in wave.picking_orders)
    if all_done:
        wave.status = WAVE_STATUS_COMPLETED

    db.commit()
    db.refresh(picking)
    return picking


def list_waves(db: Session, status: str | None = None,
               page: int = 1, page_size: int = 20) -> dict:
    query = db.query(Wave).options(
        joinedload(Wave.picking_orders).joinedload(PickingOrder.items).joinedload(PickingOrderItem.product),
        joinedload(Wave.picking_orders).joinedload(PickingOrder.outbound_order),
    )
    if status:
        query = query.filter(Wave.status == status)
    total = query.count()
    rows = (
        query.order_by(Wave.created_at.desc(), Wave.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_wave_response(w) for w in rows], "total": total,
            "page": page, "pageSize": page_size}


def list_picking_orders(db: Session, wave_id: int | None = None, status: str | None = None,
                        page: int = 1, page_size: int = 20) -> dict:
    query = db.query(PickingOrder).options(
        joinedload(PickingOrder.items).joinedload(PickingOrderItem.product),
        joinedload(PickingOrder.outbound_order),
    )
    if wave_id is not None:
        query = query.filter(PickingOrder.wave_id == wave_id)
    if status:
        query = query.filter(PickingOrder.status == status)
    total = query.count()
    rows = (
        query.order_by(PickingOrder.created_at.desc(), PickingOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_picking_response(p) for p in rows], "total": total,
            "page": page, "pageSize": page_size}
