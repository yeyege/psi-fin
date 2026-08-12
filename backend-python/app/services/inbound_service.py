"""入库单服务 — 状态机：PENDING(待收货) → COMPLETED(已收货上架)

对标领星WMS：创建入库单（到货通知）时不改变库存；
收货上架时才生成批次、累加可用库存并写流水。
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common import generate_order_no, BusinessError
from app.models import InboundOrder, InboundOrderItem, Product, Location, Batch
from app.services import inventory_service

ORDER_STATUS_PENDING = "PENDING"
ORDER_STATUS_COMPLETED = "COMPLETED"


def _build_order_response(order: InboundOrder) -> dict:
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "supplierName": order.supplier_name,
        "status": order.status,
        "remark": order.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "locationCode": it.location_code,
                "batchNo": it.batch.batch_no if it.batch else None,
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


def create_inbound_order(db: Session, data) -> InboundOrder:
    """创建入库单（PENDING，库存不变化）。校验商品与库位存在。"""
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
        order_no = generate_order_no(db, InboundOrder, "IN")
        try:
            order = InboundOrder(
                order_no=order_no,
                supplier_name=data.supplier_name,
                status=ORDER_STATUS_PENDING,
                remark=data.remark,
            )
            db.add(order)
            db.flush()
            for item in data.items:
                db.add(InboundOrderItem(
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
            raise BusinessError("入库单创建失败：单号冲突", 409)
    raise BusinessError("入库单创建失败", 500)


def get_inbound_order(db: Session, order_id: int) -> InboundOrder:
    order = db.query(InboundOrder).filter(InboundOrder.id == order_id).first()
    if not order:
        raise BusinessError("入库单不存在", 404)
    return order


def receive_inbound_order(db: Session, order_id: int) -> InboundOrder:
    """收货上架：PENDING → COMPLETED。

    生成一个批次（批次号=单号），累加各明细库存，回填批次，写流水。
    整个流程在一个事务内，任一步失败全部回滚。
    """
    order = get_inbound_order(db, order_id)
    if order.status == ORDER_STATUS_COMPLETED:
        raise BusinessError("该入库单已完成收货，不能重复操作")
    if order.status != ORDER_STATUS_PENDING:
        raise BusinessError(f"当前状态 {order.status} 不允许收货")

    from datetime import datetime
    # 每个明细行一个批次（批次号 = 单号-明细id），支持有效期/追溯
    for item in order.items:
        batch = Batch(
            batch_no=f"{order.order_no}-{item.id}",
            product_id=item.product_id,
            inbound_date=datetime.now(),
        )
        db.add(batch)
        db.flush()
        item.batch_id = batch.id
        inventory_service.add_stock(
            db,
            product_id=item.product_id,
            location_code=item.location_code,
            batch_id=batch.id,
            quantity=item.quantity,
            flow_type=inventory_service.FLOW_TYPE_INBOUND,
            order_type=inventory_service.ORDER_TYPE_INBOUND,
            order_no=order.order_no,
        )

    order.status = ORDER_STATUS_COMPLETED
    db.commit()
    db.refresh(order)
    return order


def list_inbound_orders(db: Session, status: str | None = None,
                        page: int = 1, page_size: int = 20) -> dict:
    query = db.query(InboundOrder)
    if status:
        query = query.filter(InboundOrder.status == status)
    total = query.count()
    rows = (
        query.order_by(InboundOrder.created_at.desc(), InboundOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_order_response(o) for o in rows], "total": total,
            "page": page, "pageSize": page_size}
