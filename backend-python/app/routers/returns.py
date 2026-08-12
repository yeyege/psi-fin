"""退货管理 API（FBA / 买家 / 服务商）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import ReturnOrderCreate
from app.services import return_service

router = APIRouter(prefix="/api/returns", tags=["退货管理"], dependencies=[Depends(get_current_user)])


@router.post("", status_code=201)
def create_return_order(req: ReturnOrderCreate, db: Session = Depends(get_db)):
    try:
        order = return_service.create_return_order(db, req)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 201, "message": "创建成功", "data": return_service._build_order_response(order)}


@router.post("/{order_id}/receive", status_code=200)
def receive_return_order(order_id: int, db: Session = Depends(get_db)):
    """收货登记：转正品/换标明细累加库存，报废明细只登记"""
    try:
        order = return_service.receive_return_order(db, order_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "收货成功", "data": return_service._build_order_response(order)}


@router.post("/{order_id}/finish", status_code=200)
def finish_return_order(order_id: int, db: Session = Depends(get_db)):
    """处理完成（如换标完成确认）"""
    try:
        order = return_service.finish_return_order(db, order_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "处理完成", "data": return_service._build_order_response(order)}


@router.get("")
def list_return_orders(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = return_service.list_return_orders(db, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/{order_id}")
def get_return_order(order_id: int, db: Session = Depends(get_db)):
    try:
        order = return_service.get_return_order(db, order_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "success", "data": return_service._build_order_response(order)}
