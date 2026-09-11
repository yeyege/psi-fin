"""经营驾驶舱 API — 业财核心指标 / 欠款排行 / 账龄分布 / 趋势"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import get_current_user
from app.services import finance_service

router = APIRouter(tags=["经营驾驶舱"], dependencies=[Depends(get_current_user)])


@router.get("/api/executive/summary")
def executive_summary(db: Session = Depends(get_db)):
    """应收总额 / 已回款 / 未回款 / 逾期 / 订单数与订单金额"""
    return {"code": 200, "message": "success",
            "data": finance_service.executive_summary(db)}


@router.get("/api/executive/receivable-top")
def receivable_top(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """应收余额 TOP 客户"""
    return {"code": 200, "message": "success",
            "data": finance_service.receivable_top(db, limit=limit)}


@router.get("/api/executive/aging-distribution")
def aging_distribution(db: Session = Depends(get_db)):
    """账龄分布(未到期 / 逾期1-30 / 31-60 / 60+)"""
    return {"code": 200, "message": "success",
            "data": finance_service.aging_distribution(db)}


@router.get("/api/executive/trends")
def trends(
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """订单金额与回款金额趋势"""
    return {"code": 200, "message": "success",
            "data": finance_service.trends(db, days=days)}
