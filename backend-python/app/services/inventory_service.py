"""库存查询服务 — 任务2 核心实现

职责：
1. 支持按商品名称/SKU 模糊搜索、仓库筛选、库位编码筛选
2. 多表 JOIN 返回商品名、SKU、仓库名
3. 分页（页码 + 每页条数）
4. 利用索引避免全表扫描

注意：SQLAlchemy 使用参数化查询，keyword 通过 .contains() 走绑定参数，天然防 SQL 注入。
"""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Inventory, Product, Location, Warehouse


class InventoryError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def query_inventory(
    db: Session,
    keyword: str | None = None,
    warehouse_id: int | None = None,
    location_code: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """库存查询（分页 + 筛选）。

    返回 dict: {list, total, page, page_size}
    list 中每项为 camelCase 字段的 dict，直接可序列化给前端。
    """
    query = (
        db.query(
            Inventory.product_id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("sku"),
            Inventory.location_code.label("location_code"),
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity.label("quantity"),
            Inventory.updated_at.label("updated_at"),
        )
        .join(Product, Product.id == Inventory.product_id)
        .join(Location, Location.code == Inventory.location_code)
        .join(Warehouse, Warehouse.id == Location.warehouse_id)
    )

    if keyword:
        # 模糊匹配商品名或 SKU（参数化，防注入）
        like = f"%{keyword}%"
        query = query.filter(or_(Product.name.like(like), Product.sku.like(like)))

    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)

    if location_code:
        query = query.filter(Inventory.location_code == location_code)

    # 先算总数（在不取数的情况下 count）
    total = query.count()

    # 按更新时间倒序，分页取数；加 id 作为二级排序键保证分页稳定
    # （updated_at 相同时顺序不确定，会导致跨页数据重叠）
    rows = (
        query.order_by(Inventory.updated_at.desc(), Inventory.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    list_data = [
        {
            "productId": r.product_id,
            "productName": r.product_name,
            "sku": r.sku,
            "locationCode": r.location_code,
            "warehouseName": r.warehouse_name,
            "quantity": r.quantity,
            "updatedAt": r.updated_at,
        }
        for r in rows
    ]

    return {"list": list_data, "total": total, "page": page, "pageSize": page_size}
