"""商品 SKU API"""
from fastapi import APIRouter, Depends, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, ApiResponse, PageResult
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["商品管理"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=ApiResponse[PageResult[ProductResponse]])
def list_products(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = product_service.list_products(db, keyword=keyword, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/{product_id}", response_model=ApiResponse[ProductResponse])
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = product_service.get_product(db, product_id)
    return {"code": 200, "message": "success", "data": p}


@router.post("", status_code=201, response_model=ApiResponse[ProductResponse])
def create_product(req: ProductCreate, db: Session = Depends(get_db)):
    p = product_service.create_product(db, req)
    return {"code": 201, "message": "创建成功", "data": p}


@router.put("/{product_id}", response_model=ApiResponse[ProductResponse])
def update_product(product_id: int, req: ProductUpdate, db: Session = Depends(get_db)):
    p = product_service.update_product(db, product_id, req)
    return {"code": 200, "message": "更新成功", "data": p}


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品（校验关联库存，有库存则拒绝）"""
    product_service.delete_product(db, product_id)
    return {"code": 200, "message": "删除成功", "data": None}
