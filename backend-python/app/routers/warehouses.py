"""仓库 / 库区 / 库位 API"""
from fastapi import APIRouter, Depends, Query
from app.services.auth_service import get_current_user
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WarehouseCreate, ZoneCreate, LocationCreate
from app.services import warehouse_service

router = APIRouter(tags=["仓库 & 库区 & 库位"], dependencies=[Depends(get_current_user)])


# ============ 仓库 ============

@router.get("/api/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    return {"code": 200, "message": "success", "data": warehouse_service.list_warehouses(db)}


@router.post("/api/warehouses", status_code=201)
def create_warehouse(req: WarehouseCreate, db: Session = Depends(get_db)):
    w = warehouse_service.create_warehouse(db, req)
    return {"code": 201, "message": "创建成功", "data": w}


# ============ 库区 ============

@router.get("/api/zones")
def list_zones(warehouse_id: int | None = Query(default=None, alias="warehouseId"),
               db: Session = Depends(get_db)):
    return {"code": 200, "message": "success",
            "data": warehouse_service.list_zones(db, warehouse_id=warehouse_id)}


@router.post("/api/zones", status_code=201)
def create_zone(req: ZoneCreate, db: Session = Depends(get_db)):
    z = warehouse_service.create_zone(db, req)
    return {"code": 201, "message": "创建成功", "data": z}


# ============ 库位 ============

@router.get("/api/locations")
def list_locations(warehouse_id: int | None = Query(default=None, alias="warehouseId"),
                   zone_id: int | None = Query(default=None, alias="zoneId"),
                   db: Session = Depends(get_db)):
    return {"code": 200, "message": "success",
            "data": warehouse_service.list_locations(db, warehouse_id=warehouse_id,
                                                     zone_id=zone_id)}


@router.post("/api/locations", status_code=201)
def create_location(req: LocationCreate, db: Session = Depends(get_db)):
    loc = warehouse_service.create_location(db, req)
    return {"code": 201, "message": "创建成功", "data": loc}
