"""商品 SKU 服务"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.models import Product


def list_products(db: Session, keyword: str | None = None,
                  page: int = 1, page_size: int = 20) -> dict:
    query = db.query(Product)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Product.name.like(like), Product.sku.like(like)))
    total = query.count()
    rows = (
        query.order_by(Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": rows, "total": total, "page": page, "pageSize": page_size}


def get_product(db: Session, product_id: int) -> Product:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise BusinessError("商品不存在", 404)
    return p


def create_product(db: Session, data) -> Product:
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise BusinessError(f"SKU已存在: {data.sku}")
    p = Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_product(db: Session, product_id: int, data) -> Product:
    p = get_product(db, product_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


def delete_product(db: Session, product_id: int) -> None:
    """删除商品。

    校验：有关联库存（available+locked > 0）的商品禁止删除，避免库存数据孤立。
    """
    p = get_product(db, product_id)
    from app.models import Inventory
    has_stock = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id,
                (Inventory.available_qty + Inventory.locked_qty) > 0)
        .first()
    )
    if has_stock:
        raise BusinessError(f"商品「{p.name}」仍有库存，无法删除")
    p.status = "INACTIVE"  # 软删除，保留历史流水可追溯
    db.commit()
