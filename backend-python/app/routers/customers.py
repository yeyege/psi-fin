"""客户管理 API（分层 A/B/C）"""
from fastapi import APIRouter, Depends, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CustomerCreate, CustomerUpdate, CustomerResponse, ApiResponse, PageResult
from app.services import customer_service

router = APIRouter(prefix="/api/customers", tags=["客户管理"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=ApiResponse[PageResult[CustomerResponse]])
def list_customers(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = customer_service.list_customers(db, keyword=keyword, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/{customer_id}", response_model=ApiResponse[CustomerResponse])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    c = customer_service.get_customer(db, customer_id)
    return {"code": 200, "message": "success", "data": c}


@router.post("", status_code=201, response_model=ApiResponse[CustomerResponse])
def create_customer(req: CustomerCreate, db: Session = Depends(get_db)):
    c = customer_service.create_customer(db, req)
    return {"code": 201, "message": "创建成功", "data": c}


@router.put("/{customer_id}", response_model=ApiResponse[CustomerResponse])
def update_customer(customer_id: int, req: CustomerUpdate, db: Session = Depends(get_db)):
    c = customer_service.update_customer(db, customer_id, req)
    return {"code": 200, "message": "更新成功", "data": c}


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """软删除客户"""
    customer_service.delete_customer(db, customer_id)
    return {"code": 200, "message": "删除成功", "data": None}
