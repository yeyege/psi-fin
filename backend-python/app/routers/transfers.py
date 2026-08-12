"""库内作业 API：移库 + 库存调整"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import StockTransferCreate, StockAdjustmentCreate
from app.services import transfer_service, adjustment_service

router = APIRouter(tags=["库内作业"])


def _handle(e: BusinessError):
    raise HTTPException(status_code=e.status, detail=e.message)


# ============ 移库 ============

@router.post("/api/transfers", status_code=201)
def create_transfer(req: StockTransferCreate, db: Session = Depends(get_db)):
    try:
        t = transfer_service.create_transfer(db, req)
    except BusinessError as e:
        _handle(e)
    return {"code": 201, "message": "移库完成", "data": transfer_service._build_response(t)}


@router.get("/api/transfers")
def list_transfers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    return {"code": 200, "message": "success",
            "data": transfer_service.list_transfers(db, page=page, page_size=page_size)}


# ============ 库存调整 ============

@router.post("/api/adjustments", status_code=201)
def create_adjustment(req: StockAdjustmentCreate, db: Session = Depends(get_db)):
    try:
        a = adjustment_service.create_adjustment(db, req)
    except BusinessError as e:
        _handle(e)
    return {"code": 201, "message": "调整完成", "data": adjustment_service._build_response(a)}


@router.get("/api/adjustments")
def list_adjustments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    return {"code": 200, "message": "success",
            "data": adjustment_service.list_adjustments(db, page=page, page_size=page_size)}
