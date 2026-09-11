"""财务 API — 应收台账 / 往来余额账龄 / 收款登记与核销"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ReceiptCreate, AllocateRequest
from app.services.auth_service import get_current_user
from app.services import finance_service

router = APIRouter(tags=["财务"], dependencies=[Depends(get_current_user)])


@router.get("/api/finance/receivables")
def list_receivables(
    partner_name: str | None = Query(default=None, alias="partnerName"),
    status: str | None = Query(default=None),
    only_outstanding: bool = Query(default=False, alias="onlyOutstanding"),
    only_overdue: bool = Query(default=False, alias="onlyOverdue"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """应收/应付台账，含逾期标记与未结余额"""
    data = finance_service.list_receivables(
        db, partner_name=partner_name, status=status,
        only_outstanding=only_outstanding, only_overdue=only_overdue,
        page=page, page_size=page_size,
    )
    return {"code": 200, "message": "success", "data": data}


@router.get("/api/finance/aging")
def receivable_aging(db: Session = Depends(get_db)):
    """按往来方的应收余额与账龄分布(以到期日为基准)"""
    return {"code": 200, "message": "success",
            "data": finance_service.receivable_aging(db)}


@router.post("/api/finance/receipts", status_code=201)
def register_receipt(req: ReceiptCreate, db: Session = Depends(get_db)):
    """登记收款并核销(可选)。到账金额可大于核销金额，差额为预收余额"""
    receipt = finance_service.register_receipt(db, req)
    return {"code": 201, "message": "收款登记成功",
            "data": finance_service.entry_response(receipt)}


@router.post("/api/finance/receipts/{receipt_id}/allocate")
def allocate_receipt(receipt_id: int, req: AllocateRequest, db: Session = Depends(get_db)):
    """把某笔收款的未核销余额继续核销到其他应收"""
    receipt = finance_service.allocate_receipt(db, receipt_id, req.allocations)
    return {"code": 200, "message": "核销成功",
            "data": finance_service.entry_response(receipt)}


@router.delete("/api/finance/receivables/{entry_id}")
def delete_receivable(entry_id: int, db: Session = Depends(get_db)):
    """删除应收流水(已有核销记录时禁止)"""
    finance_service.delete_receivable(db, entry_id)
    return {"code": 200, "message": "已删除", "data": None}
