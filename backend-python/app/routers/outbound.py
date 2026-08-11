"""出库 API — 选做 A

- POST /api/outbound-orders   创建出库单（并发安全扣减库存）
- GET  /api/outbound-orders   出库单列表
- GET  /api/outbound-orders/{id}  出库单详情
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OutboundOrder
from app.schemas import OutboundOrderCreate
from app.services import outbound_service

router = APIRouter(tags=["出库"])


def _to_outbound_order_dict(order) -> dict:
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "customerName": order.customer_name,
        "status": order.status,
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


@router.post("/api/outbound-orders", status_code=201)
def create_outbound_order(req: OutboundOrderCreate, db: Session = Depends(get_db)):
    """创建出库单 —— 选做 A

    库存不足时返回 409，单据不会被创建。
    """
    try:
        order = outbound_service.create_outbound_order(db, req)
    except outbound_service.OutboundError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return {
        "code": 201,
        "message": "出库单创建成功",
        "data": _to_outbound_order_dict(order),
    }


@router.get("/api/outbound-orders")
def list_outbound_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    total = db.query(OutboundOrder).count()
    orders = (
        db.query(OutboundOrder)
        .order_by(OutboundOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": [_to_outbound_order_dict(o) for o in orders],
            "total": total,
            "page": page,
            "pageSize": page_size,
        },
    }


@router.get("/api/outbound-orders/{order_id}")
def get_outbound_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="出库单不存在")
    return {"code": 200, "message": "success", "data": _to_outbound_order_dict(order)}
