"""退货单服务 — 状态机：PENDING(待收货) → RECEIVED(已收货登记) → DONE(处理完成)

对标领星 WMS 退货管理：
- 支持 FBA退货 / 买家退件 / 服务商退件 三种来源（source 字段）
- 明细 disposition 决定收货后的库存动作：
  RESELL  转正品 → 生成批次并累加可用库存（写 RETURN_IN 流水）
  RELABEL 换标后转正品 → 同 RESELL（语义标记换标需求）
  SCRAP   报废 → 只登记数量，不累加库存
"""
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.common import generate_order_no, BusinessError
from app.models import ReturnOrder, ReturnOrderItem, Product, Location, Customer, Batch
from app.services import inventory_service

ORDER_STATUS_PENDING = "PENDING"
ORDER_STATUS_RECEIVED = "RECEIVED"
ORDER_STATUS_DONE = "DONE"

# 收货后需要累加库存的处置方式
DISPOSITIONS_ADD_STOCK = ("RESELL", "RELABEL")


def _build_order_response(order: ReturnOrder) -> dict:
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "customerId": order.customer_id,
        "customerName": order.customer.name if order.customer else "",
        "source": order.source,
        "status": order.status,
        "remark": order.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "locationCode": it.location_code,
                "disposition": it.disposition,
                "batchNo": it.batch.batch_no if it.batch else None,
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


def create_return_order(db: Session, data) -> ReturnOrder:
    """创建退货单（PENDING，不改变库存）。校验客户/商品/库位存在。"""
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise BusinessError("客户不存在", 404)

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
        order_no = generate_order_no(db, ReturnOrder, "RT")
        try:
            order = ReturnOrder(
                order_no=order_no,
                customer_id=data.customer_id,
                source=data.source,
                status=ORDER_STATUS_PENDING,
                remark=data.remark,
            )
            db.add(order)
            db.flush()
            for item in data.items:
                db.add(ReturnOrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    location_code=item.location_code,
                    disposition=item.disposition,
                ))
            db.commit()
            db.refresh(order)
            return order
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("退货单创建失败：单号冲突", 409)
    raise BusinessError("退货单创建失败", 500)


def get_return_order(db: Session, order_id: int) -> ReturnOrder:
    order = db.query(ReturnOrder).filter(ReturnOrder.id == order_id).first()
    if not order:
        raise BusinessError("退货单不存在", 404)
    return order


def receive_return_order(db: Session, order_id: int) -> ReturnOrder:
    """收货登记：PENDING → RECEIVED。

    每个转正品/换标明细生成批次并累加库存（写 RETURN_IN 流水）；
    SCRAP 明细只登记，不累加库存。整个流程在一个事务内。
    """
    order = get_return_order(db, order_id)
    if order.status != ORDER_STATUS_PENDING:
        raise BusinessError(f"当前状态 {order.status} 不允许收货")

    for item in order.items:
        if item.disposition not in DISPOSITIONS_ADD_STOCK:
            continue  # 报废：只登记数量
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
            flow_type=inventory_service.FLOW_TYPE_RETURN_IN,
            order_type=inventory_service.ORDER_TYPE_RETURN,
            order_no=order.order_no,
        )

    order.status = ORDER_STATUS_RECEIVED
    db.commit()
    db.refresh(order)
    return order


def finish_return_order(db: Session, order_id: int) -> ReturnOrder:
    """处理完成：RECEIVED → DONE（如换标完成确认）。"""
    order = get_return_order(db, order_id)
    if order.status != ORDER_STATUS_RECEIVED:
        raise BusinessError(f"当前状态 {order.status} 不允许完成处理")
    order.status = ORDER_STATUS_DONE
    db.commit()
    db.refresh(order)
    return order


def list_return_orders(db: Session, status: str | None = None,
                       page: int = 1, page_size: int = 20) -> dict:
    query = db.query(ReturnOrder).options(
        joinedload(ReturnOrder.customer),
        joinedload(ReturnOrder.items).joinedload(ReturnOrderItem.product),
        joinedload(ReturnOrder.items).joinedload(ReturnOrderItem.batch),
    )
    if status:
        query = query.filter(ReturnOrder.status == status)
    total = query.count()
    rows = (
        query.order_by(ReturnOrder.created_at.desc(), ReturnOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_order_response(o) for o in rows], "total": total,
            "page": page, "pageSize": page_size}
