"""入库单 API — 状态机 PENDING → COMPLETED"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import InboundOrderCreate
from app.services import inbound_service

router = APIRouter(tags=["入库"])


def _handle(e: BusinessError):
    raise HTTPException(status_code=e.status, detail=e.message)


@router.post("/api/inbound-orders", status_code=201)
def create_inbound_order(req: InboundOrderCreate, db: Session = Depends(get_db)):
    """创建入库单（PENDING，库存未变化；收货后生效）"""
    try:
        order = inbound_service.create_inbound_order(db, req)
    except BusinessError as e:
        _handle(e)
    return {"code": 201, "message": "入库单创建成功",
            "data": inbound_service._build_order_response(order)}


@router.post("/api/inbound-orders/{order_id}/receive", status_code=200)
def receive_inbound_order(order_id: int, db: Session = Depends(get_db)):
    """收货上架：PENDING → COMPLETED，累加库存 + 生成批次 + 写流水"""
    try:
        order = inbound_service.receive_inbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "收货完成",
            "data": inbound_service._build_order_response(order)}


@router.get("/api/inbound-orders")
def list_inbound_orders(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = inbound_service.list_inbound_orders(db, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/api/inbound-orders/{order_id}")
def get_inbound_order(order_id: int, db: Session = Depends(get_db)):
    try:
        order = inbound_service.get_inbound_order(db, order_id)
    except BusinessError as e:
        _handle(e)
    return {"code": 200, "message": "success",
            "data": inbound_service._build_order_response(order)}
