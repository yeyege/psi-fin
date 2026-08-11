"""入库单服务 — 任务1 核心实现

职责：
1. 生成入库单号 IN-YYYYMMDD-XXX（按日递增）
2. 校验商品 / 库位是否存在
3. 在单个数据库事务内：创建入库单 + 明细，并累加对应库位库存
4. 异常时整体回滚，保证入库单与库存的一致性
"""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InboundOrder, InboundOrderItem, Inventory, Product, Location
from app.schemas import InboundOrderCreate


class InboundError(Exception):
    """入库业务异常"""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _generate_order_no(db: Session, prefix: str = "IN") -> str:
    """生成单号：{prefix}-YYYYMMDD-XXX，XXX 为当日递增序号。

    通过查询当日最大序号 +1 生成。并发下若发生唯一约束冲突，
    由调用方在事务中捕获 IntegrityError 并重试。
    """
    today = datetime.now().strftime("%Y%m%d")
    like = f"{prefix}-{today}-%"
    last = (
        db.query(InboundOrder)
        .filter(InboundOrder.order_no.like(like))
        .order_by(InboundOrder.order_no.desc())
        .first()
    )
    seq = int(last.order_no[-3:]) + 1 if last else 1
    return f"{prefix}-{today}-{seq:03d}"


def create_inbound_order(db: Session, req: InboundOrderCreate) -> InboundOrder:
    """创建入库单（事务性）。

    - 校验所有商品、库位存在
    - 同一单据内同一 (商品, 库位) 出现多次时合并累加
    - 库存行存在则增加，不存在则新建（upsert 语义）
    - 单号冲突时自动重试，最多 5 次
    """
    # 1. 预加载商品，避免 N+1 查询并校验存在性
    product_ids = {item.product_id for item in req.items}
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    missing_products = product_ids - products.keys()
    if missing_products:
        raise InboundError(f"商品不存在: {sorted(missing_products)}", status=404)

    # 2. 预加载库位，校验存在性
    location_codes = {item.location_code for item in req.items}
    locations = {
        loc.code: loc
        for loc in db.query(Location).filter(Location.code.in_(location_codes)).all()
    }
    missing_locs = location_codes - locations.keys()
    if missing_locs:
        raise InboundError(f"库位不存在: {sorted(missing_locs)}", status=404)

    # 3. 事务内创建入库单 + 累加库存（单号冲突则重试）
    for attempt in range(5):
        order_no = _generate_order_no(db)
        try:
            order = InboundOrder(
                order_no=order_no,
                supplier_name=req.supplier_name,
                status="COMPLETED",
            )
            db.add(order)
            db.flush()  # 拿到 order.id，但不提交

            # 聚合明细：同一 (商品, 库位) 合并，避免重复锁同一行
            aggregated: dict[tuple[int, str], int] = {}
            for item in req.items:
                aggregated[(item.product_id, item.location_code)] = (
                    aggregated.get((item.product_id, item.location_code), 0) + item.quantity
                )

            for (pid, loc_code), qty in aggregated.items():
                db.add(InboundOrderItem(
                    order_id=order.id,
                    product_id=pid,
                    quantity=qty,
                    location_code=loc_code,
                ))
                # upsert 库存
                inv = (
                    db.query(Inventory)
                    .filter(
                        Inventory.product_id == pid,
                        Inventory.location_code == loc_code,
                    )
                    .first()
                )
                if inv:
                    inv.quantity += qty
                else:
                    db.add(Inventory(product_id=pid, location_code=loc_code, quantity=qty))

            db.commit()
            db.refresh(order)
            return order
        except IntegrityError as e:
            db.rollback()
            # 单号重复 → 重试；其它唯一约束冲突直接报错
            if attempt < 4 and "order_no" in str(e.orig).lower():
                continue
            raise InboundError("入库单创建失败：数据冲突", status=409)
        except Exception:
            db.rollback()
            raise

    raise InboundError("入库单创建失败：单号生成重试耗尽", status=500)


def list_inbound_orders(db: Session, page: int = 1, page_size: int = 20) -> dict:
    """入库单列表（分页）"""
    total = db.query(InboundOrder).count()
    orders = (
        db.query(InboundOrder)
        .order_by(InboundOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"list": orders, "total": total, "page": page, "page_size": page_size}


def get_inbound_order(db: Session, order_id: int) -> InboundOrder:
    """入库单详情（含明细）"""
    order = db.query(InboundOrder).filter(InboundOrder.id == order_id).first()
    if not order:
        raise InboundError("入库单不存在", status=404)
    return order
