"""
仓库 & 库位 API — 参考实现
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Warehouse, Location

router = APIRouter(tags=["仓库 & 库位"])


@router.get("/api/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    """仓库列表"""
    warehouses = db.query(Warehouse).all()
    return {"code": 200, "message": "success", "data": warehouses}


@router.get("/api/warehouses/{warehouse_id}/locations")
def get_locations(warehouse_id: int, db: Session = Depends(get_db)):
    """某仓库下的库位列表"""
    locations = db.query(Location).filter(Location.warehouse_id == warehouse_id).all()
    return {"code": 200, "message": "success", "data": locations}
