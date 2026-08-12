"""出库单服务 — 状态机：PENDING(待拣货) → PICKED(已拣货，库存锁定) → SHIPPED(已发货，扣减)

对标领星WMS：
- 拣货(pick)：将 available 转为 locked（拣货暂存），原子操作防超卖；
- 发货(ship)：扣减 locked，写 OUTBOUND 流水；
- 任一环节库存不足则整体回滚，不留半成品。
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common import generate_order_no, BusinessError
from app.models import OutboundOrder, OutboundOrderItem, Product, Location
from app.services import inventory_service

STATUS_PENDING = "PENDING"
STATUS_PICKED = "PICKED"
STATUS_SHIPPED = "SHIPPED"


def _build_order_response(order: OutboundOrder) -> dict:
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "customerName": order.customer_name,
        "status": order.status,
        "remark": order.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "locationCode": it.location_code,
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


def create_outbound_order(db: Session, data) -> OutboundOrder:
    """创建出库单（PENDING，不改变库存）。"""
    product_ids = {i.product_id for i in data.items}
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    missing = product_ids - products.keys()
    if missing:
        raise BusinessError(f"商品不存在: {sorted(missing)}", 404)

    loc_codes = {i.location_code for i in data.items}
    locs = {
        l.code: l for l in db.query(Location).filter(Location.code.in_(loc_codes)).all()
    }
    missing_locs = loc_codes - locs.keys()
    if missing_locs:
        raise BusinessError(f"库位不存在: {sorted(missing_locs)}", 404)

    for attempt in range(5):
        order_no = generate_order_no(db, OutboundOrder, "OUT")
        try:
            order = OutboundOrder(
                order_no=order_no,
                customer_name=data.customer_name,
                status=STATUS_PENDING,
                remark=data.remark,
            )
            db.add(order)
            db.flush()
            for item in data.items:
                db.add(OutboundOrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    location_code=item.location_code,
                ))
            db.commit()
            db.refresh(order)
            return order
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("出库单创建失败：单号冲突", 409)
    raise BusinessError("出库单创建失败", 500)


def get_outbound_order(db: Session, order_id: int) -> OutboundOrder:
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise BusinessError("出库单不存在", 404)
    return order


def _require_status(order: OutboundOrder, expected: str) -> None:
    if order.status != expected:
        raise BusinessError(
            f"当前状态 {order.status} 不允许此操作（期望 {expected}）")


def pick_outbound_order(db: Session, order_id: int) -> OutboundOrder:
    """拣货：PENDING → PICKED，将可用库存锁定（防超卖）。"""
    order = get_outbound_order(db, order_id)
    _require_status(order, STATUS_PENDING)

    # 聚合明细：同一(商品,库位)合并扣减，避免重复操作同一库存行
    aggregated: dict[tuple[int, str], int] = {}
    for item in order.items:
        key = (item.product_id, item.location_code)
        aggregated[key] = aggregated.get(key, 0) + item.quantity

    for (pid, loc), qty in aggregated.items():
        ok = inventory_service.lock_stock(
            db, product_id=pid, location_code=loc, quantity=qty,
            order_type=inventory_service.ORDER_TYPE_OUTBOUND,
            order_no=order.order_no,
        )
        if not ok:
            product = db.query(Product).filter(Product.id == pid).first()
            raise BusinessError(
                f"库存不足：商品「{product.name if product else pid}」在库位 {loc} 可用库存不足 {qty} 件",
                status=409,
            )

    order.status = STATUS_PICKED
    db.commit()
    db.refresh(order)
    return order


def ship_outbound_order(db: Session, order_id: int) -> OutboundOrder:
    """发货：PICKED → SHIPPED，扣减锁定库存。"""
    order = get_outbound_order(db, order_id)
    _require_status(order, STATUS_PICKED)

    aggregated: dict[tuple[int, str], int] = {}
    for item in order.items:
        key = (item.product_id, item.location_code)
        aggregated[key] = aggregated.get(key, 0) + item.quantity

    for (pid, loc), qty in aggregated.items():
        ok = inventory_service.ship_stock(
            db, product_id=pid, location_code=loc, quantity=qty,
            order_type=inventory_service.ORDER_TYPE_OUTBOUND,
            order_no=order.order_no,
        )
        if not ok:
            product = db.query(Product).filter(Product.id == pid).first()
            raise BusinessError(
                f"锁定库存不足：商品「{product.name if product else pid}」在库位 {loc} 未锁定 {qty} 件",
                status=409,
            )

    order.status = STATUS_SHIPPED
    db.commit()
    db.refresh(order)
    return order


def list_outbound_orders(db: Session, status: str | None = None,
                         page: int = 1, page_size: int = 20) -> dict:
    query = db.query(OutboundOrder)
    if status:
        query = query.filter(OutboundOrder.status == status)
    total = query.count()
    rows = (
        query.order_by(OutboundOrder.created_at.desc(), OutboundOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_order_response(o) for o in rows], "total": total,
            "page": page, "pageSize": page_size}
