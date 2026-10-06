"""库存查询 / 流水 / 批次 API"""
from fastapi import APIRouter, Depends, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ApiResponse, PageResult, InventoryFlowResponse, BatchResponse
from app.services import inventory_service

router = APIRouter(tags=["库存"], dependencies=[Depends(get_current_user)])


@router.get("/api/inventory")
def query_inventory(
    view: str = Query(default="location", pattern="^(product|location)$"),
    keyword: str | None = Query(default=None, description="商品名称/SKU 模糊搜索"),
    warehouse_id: int | None = Query(default=None, alias="warehouseId"),
    batch_no: str | None = Query(default=None, alias="batchNo"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """库存查询

    - view=product  ：按 (商品, 仓库) 汇总可用/锁定
    - view=location ：按 (商品, 库位, 批次) 明细
    """
    result = inventory_service.query_inventory(
        db, view=view, keyword=keyword, warehouse_id=warehouse_id,
        batch_no=batch_no, page=page, page_size=page_size,
    )
    return {"code": 200, "message": "success", "data": result}


@router.get("/api/inventory/flows", response_model=ApiResponse[PageResult[InventoryFlowResponse]])
def query_flows(
    order_no: str | None = Query(default=None, alias="orderNo"),
    product_id: int | None = Query(default=None, alias="productId"),
    location_code: str | None = Query(default=None, alias="locationCode"),
    flow_type: str | None = Query(default=None, alias="flowType"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """库存流水（全量可追溯）"""
    result = inventory_service.query_flows(
        db, order_no=order_no, product_id=product_id, location_code=location_code,
        flow_type=flow_type, page=page, page_size=page_size,
    )
    return {"code": 200, "message": "success", "data": result}


@router.get("/api/inventory/batches", response_model=ApiResponse[PageResult[BatchResponse]])
def query_batches(
    keyword: str | None = Query(default=None),
    # 枚举值由 inventory_service.BATCH_STATUSES 拼出，不在路由里重写一份
    status: str | None = Query(
        default=None,
        pattern=f"^({'|'.join(inventory_service.BATCH_STATUSES)})$",
        description="按批次生命周期状态筛选；缺省返回全部",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """库存批次：每行含库龄与批次状态，可按状态筛选（非法枚举值 422）"""
    result = inventory_service.query_batches(
        db, keyword=keyword, status=status, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}
