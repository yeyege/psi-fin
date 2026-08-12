"""客户管理服务 — 分层管理（A/B/C）

对标领星：客户分层用于运营策略与计费差异化管理；
出库单/退货单均归属客户，客户不可物理删除（软删除 INACTIVE）。
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.models import Customer


def list_customers(db: Session, keyword: str | None = None,
                   page: int = 1, page_size: int = 20) -> dict:
    query = db.query(Customer)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Customer.name.like(like), Customer.code.like(like)))
    total = query.count()
    rows = (
        query.order_by(Customer.created_at.desc(), Customer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": rows, "total": total, "page": page, "pageSize": page_size}


def get_customer(db: Session, customer_id: int) -> Customer:
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise BusinessError("客户不存在", 404)
    return c


def create_customer(db: Session, data) -> Customer:
    if db.query(Customer).filter(Customer.code == data.code).first():
        raise BusinessError(f"客户编码已存在: {data.code}")
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_customer(db: Session, customer_id: int, data) -> Customer:
    c = get_customer(db, customer_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


def delete_customer(db: Session, customer_id: int) -> None:
    """软删除客户（保留历史出库/退货单可追溯）"""
    c = get_customer(db, customer_id)
    c.status = "INACTIVE"
    db.commit()
