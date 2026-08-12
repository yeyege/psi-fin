"""移库服务 — 库位间库存转移

对标领星WMS「移库」：源库位扣减可用量（MOVE_OUT），目标库位增加可用量（MOVE_IN），
双向写流水。库存不足则整单回滚。
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common import generate_order_no, BusinessError
from app.models import StockTransfer, StockTransferItem, Product, Location
from app.services import inventory_service


def _build_response(transfer: StockTransfer) -> dict:
    return {
        "id": transfer.id,
        "orderNo": transfer.order_no,
        "status": transfer.status,
        "remark": transfer.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "fromLocationCode": it.from_location_code,
                "toLocationCode": it.to_location_code,
            }
            for it in transfer.items
        ],
        "createdAt": transfer.created_at,
    }


def create_transfer(db: Session, data) -> StockTransfer:
    """创建并完成移库（单事务，任一步失败回滚）。"""
    # 校验商品与库位
    product_ids = {i.product_id for i in data.items}
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    missing = product_ids - products.keys()
    if missing:
        raise BusinessError(f"商品不存在: {sorted(missing)}", 404)

    all_locs = set()
    for i in data.items:
        all_locs.add(i.from_location_code)
        all_locs.add(i.to_location_code)
    locs = {
        l.code for l in db.query(Location).filter(Location.code.in_(all_locs)).all()
    }
    missing_locs = all_locs - locs
    if missing_locs:
        raise BusinessError(f"库位不存在: {sorted(missing_locs)}", 404)

    for attempt in range(5):
        order_no = generate_order_no(db, StockTransfer, "MV")
        try:
            transfer = StockTransfer(
                order_no=order_no,
                status="COMPLETED",
                remark=data.remark,
            )
            db.add(transfer)
            db.flush()

            for item in data.items:
                db.add(StockTransferItem(
                    transfer_id=transfer.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    from_location_code=item.from_location_code,
                    to_location_code=item.to_location_code,
                ))
                # 源库位扣减（跨批次，先扣早期批次）
                ok = inventory_service.deduct_stock(
                    db, product_id=item.product_id,
                    location_code=item.from_location_code,
                    quantity=item.quantity,
                    flow_type=inventory_service.FLOW_TYPE_MOVE_OUT,
                    order_type=inventory_service.ORDER_TYPE_TRANSFER,
                    order_no=order_no,
                )
                if not ok:
                    product = db.query(Product).filter(Product.id == item.product_id).first()
                    raise BusinessError(
                        f"库存不足：商品「{product.name if product else item.product_id}」"
                        f"在库位 {item.from_location_code} 不足 {item.quantity} 件",
                        status=409,
                    )
                # 目标库位增加（批次为 None：移库产生的库存不绑定原批次，简化处理）
                inventory_service.add_stock(
                    db, product_id=item.product_id,
                    location_code=item.to_location_code,
                    batch_id=None,
                    quantity=item.quantity,
                    flow_type=inventory_service.FLOW_TYPE_MOVE_IN,
                    order_type=inventory_service.ORDER_TYPE_TRANSFER,
                    order_no=order_no,
                )

            db.commit()
            db.refresh(transfer)
            return transfer
        except IntegrityError:
            db.rollback()
            if attempt < 4:
                continue
            raise BusinessError("移库单创建失败：单号冲突", 409)
        except BusinessError:
            db.rollback()
            raise
    raise BusinessError("移库单创建失败", 500)


def list_transfers(db: Session, page: int = 1, page_size: int = 20) -> dict:
    query = db.query(StockTransfer)
    total = query.count()
    rows = (
        query.order_by(StockTransfer.created_at.desc(), StockTransfer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": [_build_response(t) for t in rows], "total": total,
            "page": page, "pageSize": page_size}
