"""出库单 API — 状态机 PENDING → PICKED → REVIEWED → SHIPPED"""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import OutboundOrderCreate
from app.services import outbound_service

router = APIRouter(tags=["出库"], dependencies=[Depends(get_current_user)])


def _handle(e: BusinessError):
    raise HTTPException(status_code=e.status, detail=e.message)


@router.post("/api/outbound-orders", status_code=201)
def create_outbound_order(req: OutboundOrderCreate, db: Session = Depends(get_db)):
    """创建出库单（PENDING，库存未变化）"""
    try:
        order = outbound_service.create_outbound_order(db, req)
    except BusinessError as e:
        _handle(e)
    return {"code": 201, "message": "出库单创建成功",
            "data": outbound_service._build_order_response(order)}


@router.post("/api/outbound-orders/{order_id}/pick", status_code=200)
def pick_outbound_order(order_id: int, db: Session = Depends(get_db)):
    """拣货：PENDING → PICKED，锁定库存（防超卖）"""
    try:
        order = outbound_service.pick_outbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "拣货完成",
            "data": outbound_service._build_order_response(order)}


@router.post("/api/outbound-orders/{order_id}/review", status_code=200)
def review_outbound_order(order_id: int, db: Session = Depends(get_db)):
    """复核验货：PICKED → REVIEWED（发货前置环节）"""
    try:
        order = outbound_service.review_outbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "复核完成",
            "data": outbound_service._build_order_response(order)}


@router.post("/api/outbound-orders/{order_id}/ship", status_code=200)
def ship_outbound_order(order_id: int, db: Session = Depends(get_db)):
    """发货：REVIEWED → SHIPPED，扣减锁定库存"""
    try:
        order = outbound_service.ship_outbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "发货完成",
            "data": outbound_service._build_order_response(order)}


@router.get("/api/outbound-orders")
def list_outbound_orders(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = outbound_service.list_outbound_orders(db, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/api/outbound-orders/{order_id}")
def get_outbound_order(order_id: int, db: Session = Depends(get_db)):
    try:
        order = outbound_service.get_outbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "success",
            "data": outbound_service._build_order_response(order)}
