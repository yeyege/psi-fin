"""库存调整服务 — 盘盈盘亏

对标领星WMS「库存调整」：
- change_qty > 0 盘盈：增加可用库存（ADJUST_IN）
- change_qty < 0 盘亏：扣减可用库存（ADJUST_OUT），不足则报错回滚
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common import generate_order_no, BusinessError
from app.models import StockAdjustment, StockAdjustmentItem, Product, Location
from app.services import inventory_service


def _build_response(adj: StockAdjustment) -> dict:
    return {
        "id": adj.id,
        "orderNo": adj.order_no,
        "status": adj.status,
        "remark": adj.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "locationCode": it.location_code,
                "changeQty": it.change_qty,
            }
            for it in adj.items
        ],
        "createdAt": adj.created_at,
    }


def create_adjustment(db: Session, data) -> StockAdjustment:
    """创建并完成库存调整（单事务）。"""
    product_ids = {i.product_id for i in data.items}
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    missing = product_ids - products.keys()
    if missing:
        raise BusinessError(f"商品不存在: {sorted(missing)}", 404)

    loc_codes = {i.location_code for i in data.items}
    locs = {
        l.code for l in db.query(Location).filter(Location.code.in_(loc_codes)).all()
    }
    missing_locs = loc_codes - locs
    if missing_locs:
        raise BusinessError(f"库位不存在: {sorted(missing_locs)}", 404)

    for attempt in range(5):
        order_no = generate_order_no(db, StockAdjustment, "ADJ")
        try:
            adj = StockAdjustment(
                order_no=order_no,
                status="COMPLETED",
                remark=data.remark,
            )
            db.add(adj)
            db.flush()

            for item in data.items:
                db.add(StockAdjustmentItem(
                    adjustment_id=adj.id,
                    product_id=item.product_id,
                    location_code=item.location_code,
                    change_qty=item.change_qty,
                ))
                if item.change_qty > 0:
                    inventory_service.add_stock(
                        db, product_id=item.product_id,
                        location_code=item.location_code, batch_id=None,
                        quantity=item.change_qty,
                        flow_type=inventory_service.FLOW_TYPE_ADJUST_IN,
                        order_type=inventory_service.ORDER_TYPE_ADJUSTMENT,
                        order_no=order_no,
                    )
                elif item.change_qty < 0:
                    ok = inventory_service.deduct_stock(
                        db, product_id=item.product_id,
                        location_code=item.location_code,
                        quantity=-item.change_qty,
                        flow_type=inventory_service.FLOW_TYPE_ADJUST_OUT,
                        order_type=inventory_service.ORDER_TYPE_ADJUSTMENT,
                        order_no=order_no,
                    )
                    if not ok:
                        product = db.query(Product).filter(Product.id == item.product_id).first()
                        raise BusinessError(
                            f"库存不足：商品「{product.name if product else item.product_id}」"
                            f"在库位 {item.location_code} 不足以盘亏 {-item.change_qty} 件",
                            status=409,
                        )
                else:
                    raise BusinessError("调整数量不能为 0")

            db.commit()
            db.refresh(adj)
            return adj
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("库存调整创建失败：单号冲突", 409)
        except BusinessError:
            db.rollback()
            raise
    raise BusinessError("库存调整创建失败", 500)


def list_adjustments(db: Session, page: int = 1, page_size: int = 20) -> dict:
    query = db.query(StockAdjustment)
    total = query.count()
    rows = (
        query.order_by(StockAdjustment.created_at.desc(), StockAdjustment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_response(a) for a in rows], "total": total,
            "page": page, "pageSize": page_size}
