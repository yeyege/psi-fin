"""仓库 / 库区 / 库位服务"""
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.models import Warehouse, Zone, Location


# ============ 仓库 ============

def list_warehouses(db: Session) -> list[Warehouse]:
    return db.query(Warehouse).filter(Warehouse.status == "ACTIVE").all()


def create_warehouse(db: Session, data) -> Warehouse:
    if db.query(Warehouse).filter(Warehouse.code == data.code).first():
        raise BusinessError(f"仓库编码已存在: {data.code}")
    w = Warehouse(code=data.code, name=data.name)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


# ============ 库区 ============

def get_zone(db: Session, zone_id: int) -> Zone:
    z = db.query(Zone).filter(Zone.id == zone_id).first()
    if not z:
        raise BusinessError("库区不存在", 404)
    return z


def list_zones(db: Session, warehouse_id: int | None = None) -> list[Zone]:
    query = db.query(Zone)
    if warehouse_id is not None:
        query = query.filter(Zone.warehouse_id == warehouse_id)
    return query.order_by(Zone.id.asc()).all()


def create_zone(db: Session, data) -> Zone:
    get_warehouse(db, data.warehouse_id)
    z = Zone(
        warehouse_id=data.warehouse_id,
        code=data.code,
        name=data.name,
        zone_type=data.zone_type,
    )
    db.add(z)
    db.commit()
    db.refresh(z)
    return z


# ============ 库位 ============

def get_warehouse(db: Session, warehouse_id: int) -> Warehouse:
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not w:
        raise BusinessError("仓库不存在", 404)
    return w


def get_location(db: Session, location_code: str) -> Location:
    loc = db.query(Location).filter(Location.code == location_code).first()
    if not loc:
        raise BusinessError(f"库位不存在: {location_code}", 404)
    return loc


def list_locations(db: Session, warehouse_id: int | None = None,
                   zone_id: int | None = None) -> list[Location]:
    query = db.query(Location)
    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)
    if zone_id is not None:
        query = query.filter(Location.zone_id == zone_id)
    # 推荐上架按优先级排序（领星：priority 越大越优先）
    return query.order_by(Location.priority.desc(), Location.id.asc()).all()


def create_location(db: Session, data) -> Location:
    get_zone(db, data.zone_id)
    get_warehouse(db, data.warehouse_id)
    if db.query(Location).filter(Location.code == data.code).first():
        raise BusinessError(f"库位编码已存在: {data.code}")
    loc = Location(
        zone_id=data.zone_id,
        warehouse_id=data.warehouse_id,
        code=data.code,
        priority=data.priority,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc
