"""
库存 & 入库 API

- POST /api/inbound-orders        创建入库单（任务1）
- GET  /api/inbound-orders        入库单列表
- GET  /api/inbound-orders/{id}   入库单详情
- GET  /api/inventory             库存查询（任务2）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InboundOrderCreate
from app.services import inbound_service, inventory_service

router = APIRouter(tags=["库存 & 入库"])


def _to_inbound_order_dict(order) -> dict:
    """将入库单 ORM 对象转为 camelCase 响应 dict（含明细）。"""
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "supplierName": order.supplier_name,
        "status": order.status,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product.name if it.product else "",
                "quantity": it.quantity,
                "locationCode": it.location_code,
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


@router.post("/api/inbound-orders", status_code=201)
def create_inbound_order(req: InboundOrderCreate, db: Session = Depends(get_db)):
    """创建入库单 —— 任务1

    - 自动生成单号 IN-YYYYMMDD-XXX
    - 校验商品 / 库位存在
    - 事务内创建入库单 + 累加库存，保证一致性
    """
    try:
        order = inbound_service.create_inbound_order(db, req)
    except inbound_service.InboundError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return {
        "code": 201,
        "message": "入库单创建成功",
        "data": _to_inbound_order_dict(order),
    }


@router.get("/api/inbound-orders")
def list_inbound_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """入库单列表（分页）"""
    result = inbound_service.list_inbound_orders(db, page=page, page_size=page_size)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": [_to_inbound_order_dict(o) for o in result["list"]],
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["page_size"],
        },
    }


@router.get("/api/inbound-orders/{order_id}")
def get_inbound_order(order_id: int, db: Session = Depends(get_db)):
    """入库单详情"""
    try:
        order = inbound_service.get_inbound_order(db, order_id)
    except inbound_service.InboundError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return {"code": 200, "message": "success", "data": _to_inbound_order_dict(order)}


@router.get("/api/inventory")
def query_inventory(
    keyword: str | None = Query(default=None, description="商品名称/SKU 模糊搜索"),
    warehouse_id: int | None = Query(default=None, alias="warehouseId", description="仓库ID"),
    location_code: str | None = Query(default=None, alias="locationCode", description="库位编码"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """库存查询 —— 任务2

    - 支持按 keyword 模糊搜索（商品名/SKU）
    - 支持按 warehouseId / locationCode 筛选
    - 支持分页
    - JOIN 返回商品名、SKU、仓库名
    """
    result = inventory_service.query_inventory(
        db,
        keyword=keyword,
        warehouse_id=warehouse_id,
        location_code=location_code,
        page=page,
        page_size=page_size,
    )
    return {"code": 200, "message": "success", "data": result}
