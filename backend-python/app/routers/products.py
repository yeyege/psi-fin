"""商品 SKU API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.schemas import ProductCreate, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["商品管理"])


@router.get("")
def list_products(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    result = product_service.list_products(db, keyword=keyword, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    try:
        p = product_service.get_product(db, product_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "success", "data": p}


@router.post("", status_code=201)
def create_product(req: ProductCreate, db: Session = Depends(get_db)):
    try:
        p = product_service.create_product(db, req)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 201, "message": "创建成功", "data": p}


@router.put("/{product_id}")
def update_product(product_id: int, req: ProductUpdate, db: Session = Depends(get_db)):
    try:
        p = product_service.update_product(db, product_id, req)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "更新成功", "data": p}


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """删除商品（校验关联库存，有库存则拒绝）"""
    try:
        product_service.delete_product(db, product_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"code": 200, "message": "删除成功", "data": None}
