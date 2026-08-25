"""盘点 API（库存准确率闭环）"""
from fastapi import APIRouter, Depends, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CountCreate, CountSubmit
from app.services import count_service

router = APIRouter(prefix="/api/counts", tags=["盘点管理"], dependencies=[Depends(get_current_user)])


@router.post("", status_code=201)
def create_count(req: CountCreate, db: Session = Depends(get_db)):
    count = count_service.create_count_order(db, req)
    return {"code": 201, "message": "盘点单创建成功",
            "data": count_service._build_response(count)}


@router.get("")
def list_counts(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = count_service.list_counts(db, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/{count_id}")
def get_count(count_id: int, db: Session = Depends(get_db)):
    count = count_service.get_count_order(db, count_id)
    return {"code": 200, "message": "success",
            "data": count_service._build_response(count)}


@router.post("/{count_id}/submit", status_code=200)
def submit_count(count_id: int, req: CountSubmit, db: Session = Depends(get_db)):
    """录入实盘数量（可多次提交覆盖）"""
    count = count_service.submit_count_items(db, count_id, req.items)
    return {"code": 200, "message": "实盘数量已保存",
            "data": count_service._build_response(count)}


@router.post("/{count_id}/complete", status_code=200)
def complete_count(count_id: int, db: Session = Depends(get_db)):
    """完成盘点：差异自动生成盘盈/盘亏调整单 + 流水留痕"""
    count = count_service.complete_count(db, count_id)
    return {"code": 200, "message": "盘点完成，差异已自动调整",
            "data": count_service._build_response(count)}
