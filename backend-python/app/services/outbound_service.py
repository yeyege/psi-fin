"""出库单服务 — 选做 A

核心难点：库存扣减的并发安全（防止超卖）。

方案选择：原子条件 UPDATE（乐观式 CAS 语义）
-----------------------------------------------------------------
对每条明细执行：
    UPDATE inventory
       SET quantity = quantity - :q
     WHERE product_id = :pid
       AND location_code = :loc
       AND quantity >= :q        -- 关键：扣减前置校验

- 该 UPDATE 在数据库层是原子的（单行行锁），把「检查库存充足」与「扣减」合并为一条语句，
  彻底消除「先查后扣」的 TOCTOU 竞态窗口。
- 通过 rowcount 判断是否扣减成功：0 表示库存不足或行不存在 → 整单回滚并报错。
- 整个出库单在单个事务内，任一明细失败则全部回滚，保证单据与库存一致。

为何不用悲观锁 / 版本号：
- 悲悲观锁（SELECT ... FOR UPDATE）在 SQLite 支持有限，且会降低并发吞吐。
- 版本号（乐观锁）需要额外的 version 列与重试逻辑；而本场景「扣减」本身可用一条 SQL
  表达，原子 UPDATE 更简洁且无需重试。
- 该方案对 PostgreSQL/MySQL 同样适用，迁移无成本。
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import OutboundOrder, OutboundOrderItem, Product, Location, Inventory
from app.schemas import OutboundOrderCreate


class OutboundError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _generate_order_no(db: Session, prefix: str = "OUT") -> str:
    """生成单号：OUT-YYYYMMDD-XXX"""
    today = datetime.now().strftime("%Y%m%d")
    like = f"{prefix}-{today}-%"
    last = (
        db.query(OutboundOrder)
        .filter(OutboundOrder.order_no.like(like))
        .order_by(OutboundOrder.order_no.desc())
        .first()
    )
    seq = int(last.order_no[-3:]) + 1 if last else 1
    return f"{prefix}-{today}-{seq:03d}"


def create_outbound_order(db: Session, req: OutboundOrderCreate) -> OutboundOrder:
    """创建出库单（事务性 + 并发安全扣减）。

    库存不足 / 商品 / 库位不存在时抛 OutboundError，事务回滚，不会留下半成品单据。
    """
    # 1. 校验商品
    product_ids = {item.product_id for item in req.items}
    products = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    missing_products = product_ids - products.keys()
    if missing_products:
        raise OutboundError(f"商品不存在: {sorted(missing_products)}", status=404)

    # 2. 校验库位
    location_codes = {item.location_code for item in req.items}
    locations = {
        loc.code: loc
        for loc in db.query(Location).filter(Location.code.in_(location_codes)).all()
    }
    missing_locs = location_codes - locations.keys()
    if missing_locs:
        raise OutboundError(f"库位不存在: {sorted(missing_locs)}", status=404)

    # 3. 聚合明细：同一 (商品, 库位) 合并，避免对同一库存行多次扣减
    aggregated: dict[tuple[int, str], int] = {}
    for item in req.items:
        aggregated[(item.product_id, item.location_code)] = (
            aggregated.get((item.product_id, item.location_code), 0) + item.quantity
        )

    # 4. 事务内：创建单据 + 原子扣减库存
    order_no = _generate_order_no(db)
    try:
        order = OutboundOrder(
            order_no=order_no,
            customer_name=req.customer_name,
            status="COMPLETED",
        )
        db.add(order)
        db.flush()

        for (pid, loc_code), qty in aggregated.items():
            # 原子条件扣减：quantity >= qty 才扣，返回受影响行数
            result = db.query(Inventory).filter(
                Inventory.product_id == pid,
                Inventory.location_code == loc_code,
                Inventory.quantity >= qty,
            ).update(
                {Inventory.quantity: Inventory.quantity - qty},
                synchronize_session=False,
            )
            if result == 0:
                # 库存不足或库存行不存在
                product_name = products[pid].name
                raise OutboundError(
                    f"库存不足：商品「{product_name}」在库位 {loc_code} 的库存不足以出库 {qty} 件",
                    status=409,
                )

            db.add(OutboundOrderItem(
                order_id=order.id,
                product_id=pid,
                quantity=qty,
                location_code=loc_code,
            ))

        db.commit()
        db.refresh(order)
        return order
    except OutboundError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
