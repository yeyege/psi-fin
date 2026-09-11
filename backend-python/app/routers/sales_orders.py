"""销售订单 API — 草稿 → 确认 → 发货(生成应收) → 完成 / 作废"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SalesOrderCreate, SalesOrderUpdate, SalesOrderShip
from app.services.auth_service import get_current_user
from app.services import finance_service

router = APIRouter(tags=["销售订单"], dependencies=[Depends(get_current_user)])


@router.post("/api/sales-orders", status_code=201)
def create_sales_order(req: SalesOrderCreate, db: Session = Depends(get_db)):
    """创建销售订单(草稿)，金额由明细汇总"""
    order = finance_service.create_sales_order(db, req)
    return {"code": 201, "message": "销售订单创建成功",
            "data": finance_service.order_response(order)}


@router.get("/api/sales-orders")
def list_sales_orders(
    status: str | None = Query(default=None),
    customer_id: int | None = Query(default=None, alias="customerId"),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
):
    data = finance_service.list_sales_orders(
        db, status=status, customer_id=customer_id, keyword=keyword,
        page=page, page_size=page_size,
    )
    return {"code": 200, "message": "success", "data": data}


@router.get("/api/sales-orders/{order_id}")
def get_sales_order(order_id: int, db: Session = Depends(get_db)):
    order = finance_service.get_sales_order(db, order_id)
    return {"code": 200, "message": "success",
            "data": finance_service.order_response(order)}


@router.put("/api/sales-orders/{order_id}")
def update_sales_order(order_id: int, req: SalesOrderUpdate, db: Session = Depends(get_db)):
    """编辑订单(仅草稿):改账期/备注/明细，明细变更后重算金额"""
    order = finance_service.update_sales_order(db, order_id, req)
    return {"code": 200, "message": "订单已更新",
            "data": finance_service.order_response(order)}


@router.post("/api/sales-orders/{order_id}/confirm")
def confirm_sales_order(order_id: int, db: Session = Depends(get_db)):
    order = finance_service.confirm_sales_order(db, order_id)
    return {"code": 200, "message": "订单已确认",
            "data": finance_service.order_response(order)}


@router.post("/api/sales-orders/{order_id}/ship")
def ship_sales_order(order_id: int, req: SalesOrderShip | None = None,
                     db: Session = Depends(get_db)):
    """发货：已确认 → 已发货，并自动生成应收（幂等）"""
    outbound_no = req.outbound_order_no if req else None
    order = finance_service.ship_sales_order(db, order_id, outbound_order_no=outbound_no)
    return {"code": 200, "message": "订单已发货，应收已生成",
            "data": finance_service.order_response(order)}


@router.post("/api/sales-orders/{order_id}/complete")
def complete_sales_order(order_id: int, db: Session = Depends(get_db)):
    order = finance_service.complete_sales_order(db, order_id)
    return {"code": 200, "message": "订单已完成",
            "data": finance_service.order_response(order)}


@router.post("/api/sales-orders/{order_id}/cancel")
def cancel_sales_order(order_id: int, db: Session = Depends(get_db)):
    order = finance_service.cancel_sales_order(db, order_id)
    return {"code": 200, "message": "订单已作废",
            "data": finance_service.order_response(order)}
