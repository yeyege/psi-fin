"""波次拣货 API（智能波次策略）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import WaveCreate
from app.services import wave_service

router = APIRouter(prefix="/api/waves", tags=["波次拣货"])


@router.post("", status_code=201)
def create_wave(req: WaveCreate, db: Session = Depends(get_db)):
    try:
        wave = wave_service.create_wave(db, req.outbound_order_ids, remark=req.remark)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 201, "message": "波次生成成功",
            "data": wave_service._build_wave_response(wave)}


@router.get("")
def list_waves(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = wave_service.list_waves(db, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/picking-orders")
def list_picking_orders(
    wave_id: int | None = Query(default=None, alias="waveId"),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = wave_service.list_picking_orders(db, wave_id=wave_id, status=status,
                                              page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.post("/picking-orders/{picking_id}/pick", status_code=200)
def pick_picking_order(picking_id: int, db: Session = Depends(get_db)):
    """执行拣货：锁定库存（防超卖），出库单进入 PICKED"""
    try:
        picking = wave_service.pick_picking_order(db, picking_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "拣货完成", "data": wave_service._build_picking_response(picking)}


@router.get("/{wave_id}")
def get_wave(wave_id: int, db: Session = Depends(get_db)):
    try:
        wave = wave_service.get_wave(db, wave_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "success", "data": wave_service._build_wave_response(wave)}
