"""数据看板 API（首页统计）"""
from fastapi import APIRouter, Depends
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["数据看板"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return {"code": 200, "message": "success", "data": dashboard_service.dashboard_summary(db)}
