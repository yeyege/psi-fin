"""业财一体服务 — 销售订单 + 发货生成应收 + 收款核销 + 账龄/驾驶舱聚合

业务口径(见 openspec/changes/add-business-finance/design.md):
- 应收在【发货】动作内生成,到期日 = 发货日期 + 账期
- 幂等三层:服务层预查 + DB 唯一约束(source_order_no, entry_type) + IntegrityError 兜底
- 核销支持部分核销;收款可大于已核销金额,差额为未核销余额(预收)
- 账龄以【到期日】为基准实时分段,不落库
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.common import generate_order_no, BusinessError
from app.models import (
    Customer, Product, SalesOrder, SalesOrderItem,
    FinanceEntry, FinanceSettlement,
)

# ============ 常量 ============

ORDER_DRAFT = "DRAFT"
ORDER_CONFIRMED = "CONFIRMED"
ORDER_SHIPPED = "SHIPPED"
ORDER_COMPLETED = "COMPLETED"
ORDER_CANCELLED = "CANCELLED"

ENTRY_RECEIVABLE = "RECEIVABLE"
ENTRY_PAYABLE = "PAYABLE"
ENTRY_RECEIPT = "RECEIPT"
ENTRY_PAYMENT = "PAYMENT"

PARTNER_CUSTOMER = "CUSTOMER"
PARTNER_SUPPLIER = "SUPPLIER"

ENTRY_OPEN = "OPEN"
ENTRY_PARTIAL = "PARTIAL"
ENTRY_SETTLED = "SETTLED"

RECEIVABLE_TYPES = (ENTRY_RECEIVABLE, ENTRY_PAYABLE)
SETTLEMENT_TYPES = (ENTRY_RECEIPT, ENTRY_PAYMENT)


def _r(value) -> float:
    """金额统一保留 2 位小数"""
    return round(float(value or 0), 2)


def _derive_status(amount: float, settled: float) -> str:
    if settled <= 0:
        return ENTRY_OPEN
    if settled + 1e-9 >= amount:
        return ENTRY_SETTLED
    return ENTRY_PARTIAL


def _outstanding(entry: FinanceEntry) -> float:
    return _r(entry.amount - entry.settled_amount)


# ============ 响应构造 ============

def order_response(order: SalesOrder) -> dict:
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "customerId": order.customer_id,
        "customerName": order.customer_name,
        "status": order.status,
        "creditDays": order.credit_days,
        "totalAmount": _r(order.total_amount),
        "outboundOrderNo": order.outbound_order_no,
        "shippedAt": order.shipped_at,
        "remark": order.remark,
        "items": [
            {
                "productId": it.product_id,
                "productName": it.product_name,
                "quantity": it.quantity,
                "unitPrice": _r(it.unit_price),
                "amount": _r(it.amount),
            }
            for it in order.items
        ],
        "createdAt": order.created_at,
    }


def entry_response(entry: FinanceEntry, today: date | None = None) -> dict:
    today = today or date.today()
    return {
        "id": entry.id,
        "entryNo": entry.entry_no,
        "entryType": entry.entry_type,
        "partnerType": entry.partner_type,
        "partnerId": entry.partner_id,
        "partnerName": entry.partner_name,
        "sourceOrderNo": entry.source_order_no,
        "amount": _r(entry.amount),
        "settledAmount": _r(entry.settled_amount),
        "outstanding": _outstanding(entry),
        "occurredDate": entry.occurred_date,
        "dueDate": entry.due_date,
        "status": entry.status,
        "overdue": bool(entry.due_date and entry.due_date < today and _outstanding(entry) > 0),
        "remark": entry.remark,
        "createdAt": entry.created_at,
    }


# ============ 销售订单 ============

def _gen_no_with_retry(db: Session, model, prefix: str, no_col: str = "order_no") -> str:
    return generate_order_no(db, model, prefix, no_col=no_col)


def create_sales_order(db: Session, data) -> SalesOrder:
    """创建销售订单(草稿)。金额 = Σ(数量 × 单价)。"""
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise BusinessError("客户不存在", 404)
    if not data.items:
        raise BusinessError("销售订单至少需要一条明细")

    product_ids = {i.product_id for i in data.items}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    missing = product_ids - products.keys()
    if missing:
        raise BusinessError(f"商品不存在: {sorted(missing)}", 404)

    total = _r(sum(_r(i.quantity * i.unit_price) for i in data.items))

    for _ in range(5):
        order_no = _gen_no_with_retry(db, SalesOrder, "SO")
        try:
            order = SalesOrder(
                order_no=order_no,
                customer_id=customer.id,
                customer_name=customer.name,
                status=ORDER_DRAFT,
                credit_days=data.credit_days or 0,
                total_amount=total,
                remark=data.remark,
            )
            db.add(order)
            db.flush()
            for i in data.items:
                db.add(SalesOrderItem(
                    order_id=order.id,
                    product_id=i.product_id,
                    product_name=products[i.product_id].name,
                    quantity=i.quantity,
                    unit_price=_r(i.unit_price),
                    amount=_r(i.quantity * i.unit_price),
                ))
            db.commit()
            db.refresh(order)
            return order
        except IntegrityError:
            db.rollback()
    raise BusinessError("销售订单创建失败:单号冲突", 409)


def get_sales_order(db: Session, order_id: int) -> SalesOrder:
    order = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.items))
        .filter(SalesOrder.id == order_id)
        .first()
    )
    if not order:
        raise BusinessError("销售订单不存在", 404)
    return order


def list_sales_orders(db: Session, status: str | None = None, customer_id: int | None = None,
                      keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    query = db.query(SalesOrder).options(joinedload(SalesOrder.items))
    if status:
        query = query.filter(SalesOrder.status == status)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (SalesOrder.order_no.like(like)) | (SalesOrder.customer_name.like(like))
        )
    total = query.count()
    rows = (
        query.order_by(SalesOrder.created_at.desc(), SalesOrder.id.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return {"list": [order_response(o) for o in rows], "total": total,
            "page": page, "pageSize": page_size}


def update_sales_order(db: Session, order_id: int, data) -> SalesOrder:
    """编辑订单(仅草稿):可改账期/备注/明细,明细变更后重算金额。"""
    order = get_sales_order(db, order_id)
    if order.status != ORDER_DRAFT:
        raise BusinessError(f"当前状态 {order.status} 不允许编辑订单")

    if data.credit_days is not None:
        order.credit_days = data.credit_days
    if data.remark is not None:
        order.remark = data.remark

    if data.items is not None:
        if not data.items:
            raise BusinessError("销售订单至少需要一条明细")
        product_ids = {i.product_id for i in data.items}
        products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
        missing = product_ids - products.keys()
        if missing:
            raise BusinessError(f"商品不存在: {sorted(missing)}", 404)
        order.items.clear()  # cascade delete-orphan 删除旧明细
        db.flush()
        for i in data.items:
            db.add(SalesOrderItem(
                order_id=order.id,
                product_id=i.product_id,
                product_name=products[i.product_id].name,
                quantity=i.quantity,
                unit_price=_r(i.unit_price),
                amount=_r(i.quantity * i.unit_price),
            ))
        order.total_amount = _r(sum(_r(i.quantity * i.unit_price) for i in data.items))

    db.commit()
    db.refresh(order)
    return order


def confirm_sales_order(db: Session, order_id: int) -> SalesOrder:
    """草稿 → 已确认。"""
    order = get_sales_order(db, order_id)
    if order.status != ORDER_DRAFT:
        raise BusinessError(f"当前状态 {order.status} 不允许确认")
    order.status = ORDER_CONFIRMED
    db.commit()
    db.refresh(order)
    return order


def ship_sales_order(db: Session, order_id: int, outbound_order_no: str | None = None) -> SalesOrder:
    """已确认 → 已发货,并在同一事务内生成应收(幂等)。"""
    order = get_sales_order(db, order_id)
    if order.status == ORDER_SHIPPED:
        raise BusinessError("该订单已发货,不能重复发货")
    if order.status != ORDER_CONFIRMED:
        raise BusinessError(f"当前状态 {order.status} 不允许发货")

    order.status = ORDER_SHIPPED
    order.shipped_at = datetime.now()
    if outbound_order_no:
        order.outbound_order_no = outbound_order_no
    db.flush()

    try:
        _generate_receivable(db, order)
    except Exception:
        db.rollback()  # 应收生成失败则整单失败,不留下"已发货却没有应收"的中间态
        raise

    db.commit()
    db.refresh(order)
    return order


def complete_sales_order(db: Session, order_id: int) -> SalesOrder:
    """已发货 → 已完成。"""
    order = get_sales_order(db, order_id)
    if order.status != ORDER_SHIPPED:
        raise BusinessError(f"当前状态 {order.status} 不允许完成")
    order.status = ORDER_COMPLETED
    db.commit()
    db.refresh(order)
    return order


def cancel_sales_order(db: Session, order_id: int) -> SalesOrder:
    """草稿/已确认 → 已作废(已发货后不可作废)。"""
    order = get_sales_order(db, order_id)
    if order.status not in (ORDER_DRAFT, ORDER_CONFIRMED):
        raise BusinessError(f"当前状态 {order.status} 不允许作废")
    order.status = ORDER_CANCELLED
    db.commit()
    db.refresh(order)
    return order


# ============ 应收生成(幂等) ============

def _generate_receivable(db: Session, order: SalesOrder) -> FinanceEntry:
    """由已发货订单生成应收:预查 + 唯一约束 + IntegrityError 兜底,保证幂等。"""
    existing = (
        db.query(FinanceEntry)
        .filter(FinanceEntry.source_order_no == order.order_no,
                FinanceEntry.entry_type == ENTRY_RECEIVABLE)
        .first()
    )
    if existing:
        return existing

    occurred = (order.shipped_at or datetime.now()).date()
    due = occurred + timedelta(days=order.credit_days or 0)
    for _ in range(5):
        entry = FinanceEntry(
            entry_no=_gen_no_with_retry(db, FinanceEntry, "AR", no_col="entry_no"),
            entry_type=ENTRY_RECEIVABLE,
            partner_type=PARTNER_CUSTOMER,
            partner_id=order.customer_id,
            partner_name=order.customer_name,
            source_order_no=order.order_no,
            amount=_r(order.total_amount),
            settled_amount=0,
            occurred_date=occurred,
            due_date=due,
            status=ENTRY_OPEN,
            remark=f"销售订单 {order.order_no} 发货生成",
        )
        try:
            db.add(entry)
            db.flush()
            return entry
        except IntegrityError:
            # 唯一约束兜底:并发下该订单应收已存在,交由调用方回滚(不产生第二条)
            raise BusinessError(f"订单 {order.order_no} 的应收已存在(并发冲突),请重试", 409)


def generate_receivable_for_order(db: Session, order: SalesOrder) -> FinanceEntry:
    """供测试/补偿使用的显式入口(仍幂等)。"""
    entry = _generate_receivable(db, order)
    db.commit()
    return entry


# ============ 收款与核销 ============

def _validate_allocations(db: Session, allocations, available: float) -> None:
    """核销前校验(只读,不写库):目标存在 / 类型正确 / 金额为正 / 不超单张未结 / 合计不超可核销余额。

    先校验后写入,避免依赖嵌套事务(SQLite/pysqlite 对 SAVEPOINT 支持不可靠)。
    """
    if not allocations:
        return
    total = _r(sum(_r(a.amount) for a in allocations))
    if total > _r(available) + 1e-9:
        raise BusinessError(f"核销金额 {total} 超过可核销余额 {_r(available)}")
    for alloc in allocations:
        if _r(alloc.amount) <= 0:
            raise BusinessError("核销金额必须大于 0")
        target = db.query(FinanceEntry).filter(FinanceEntry.id == alloc.target_entry_id).first()
        if not target:
            raise BusinessError(f"应收流水不存在: {alloc.target_entry_id}", 404)
        if target.entry_type not in RECEIVABLE_TYPES:
            raise BusinessError("只能核销到应收/应付流水")
        outstanding = _outstanding(target)
        if _r(alloc.amount) > outstanding + 1e-9:
            raise BusinessError(
                f"核销金额 {_r(alloc.amount)} 超过应收 {target.entry_no} 未结余额 {outstanding}"
            )


def _apply_settlements(db: Session, receipt: FinanceEntry, allocations) -> None:
    """把核销明细写入并更新收款与目标状态(调用前应已通过 _validate_allocations)。"""
    if not allocations:
        return
    total_alloc = _r(sum(_r(a.amount) for a in allocations))
    for alloc in allocations:
        target = db.query(FinanceEntry).filter(FinanceEntry.id == alloc.target_entry_id).first()
        db.add(FinanceSettlement(
            receipt_entry_id=receipt.id,
            target_entry_id=target.id,
            amount=_r(alloc.amount),
        ))
        target.settled_amount = _r(target.settled_amount + _r(alloc.amount))
        target.status = _derive_status(target.amount, target.settled_amount)

    receipt.settled_amount = _r(receipt.settled_amount + total_alloc)
    receipt.status = _derive_status(receipt.amount, receipt.settled_amount)


def _create_settlement_entry(db: Session, entry_type: str, prefix: str, data) -> FinanceEntry:
    for _ in range(5):
        entry = FinanceEntry(
            entry_no=_gen_no_with_retry(db, FinanceEntry, prefix, no_col="entry_no"),
            entry_type=entry_type,
            partner_type=data.partner_type or PARTNER_CUSTOMER,
            partner_id=data.partner_id,
            partner_name=data.partner_name,
            source_order_no=None,
            amount=_r(data.amount),
            settled_amount=0,
            occurred_date=data.occurred_date or date.today(),
            due_date=None,
            status=ENTRY_OPEN,
            remark=data.remark,
        )
        try:
            db.add(entry)
            db.flush()
            return entry
        except IntegrityError:
            db.rollback()  # 此处尚无外层改动,回滚安全,重新生成单号
            continue
    raise BusinessError("收款登记失败:单号冲突", 409)


def register_receipt(db: Session, data) -> FinanceEntry:
    """登记收款并核销(可选)。收款金额可大于核销金额,差额保留为未核销余额(预收)。"""
    if _r(data.amount) <= 0:
        raise BusinessError("收款金额必须大于 0")

    allocations = data.allocations or []
    # 先校验(只读),校验不过就不落任何数据
    _validate_allocations(db, allocations, _r(data.amount))

    receipt = _create_settlement_entry(db, ENTRY_RECEIPT, "RC", data)
    _apply_settlements(db, receipt, allocations)
    db.commit()
    db.refresh(receipt)
    return receipt


def allocate_receipt(db: Session, receipt_entry_id: int, allocations) -> FinanceEntry:
    """把某笔收款/付款的未核销余额继续核销到其他应收/应付。"""
    receipt = db.query(FinanceEntry).filter(FinanceEntry.id == receipt_entry_id).first()
    if not receipt:
        raise BusinessError("收款流水不存在", 404)
    if receipt.entry_type not in SETTLEMENT_TYPES:
        raise BusinessError("只有收款/付款流水可以执行核销")
    # 先校验(只读),校验不过就不做任何改动
    _validate_allocations(db, allocations, _r(receipt.amount - receipt.settled_amount))
    _apply_settlements(db, receipt, allocations)
    db.commit()
    db.refresh(receipt)
    return receipt


# ============ 应收查询 / 余额 / 账龄 ============

def list_receivables(db: Session, partner_name: str | None = None, status: str | None = None,
                     only_outstanding: bool = False, only_overdue: bool = False,
                     page: int = 1, page_size: int = 20) -> dict:
    query = db.query(FinanceEntry).filter(FinanceEntry.entry_type.in_(RECEIVABLE_TYPES))
    if partner_name:
        query = query.filter(FinanceEntry.partner_name.like(f"%{partner_name}%"))
    if status:
        query = query.filter(FinanceEntry.status == status)
    rows = query.order_by(FinanceEntry.due_date.asc(), FinanceEntry.id.desc()).all()

    today = date.today()
    if only_outstanding:
        rows = [r for r in rows if _outstanding(r) > 0]
    if only_overdue:
        rows = [r for r in rows if r.due_date and r.due_date < today and _outstanding(r) > 0]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]
    return {"list": [entry_response(e, today) for e in page_rows], "total": total,
            "page": page, "pageSize": page_size}


def _aging_bucket(due_date: date | None, today: date) -> str:
    """账龄分段(以到期日为基准)"""
    if due_date is None or due_date >= today:
        return "notDue"
    overdue_days = (today - due_date).days
    if overdue_days <= 30:
        return "days1to30"
    if overdue_days <= 60:
        return "days31to60"
    return "days60plus"


def receivable_aging(db: Session) -> list[dict]:
    """按往来方汇总应收余额与账龄分布(以到期日为基准)。"""
    today = date.today()
    entries = (
        db.query(FinanceEntry)
        .filter(FinanceEntry.entry_type == ENTRY_RECEIVABLE)
        .all()
    )
    buckets = ("notDue", "days1to30", "days31to60", "days60plus")
    result: dict[str, dict] = {}
    for e in entries:
        outstanding = _outstanding(e)
        if outstanding <= 0:
            continue
        row = result.setdefault(e.partner_name, {
            "partnerName": e.partner_name,
            "receivableTotal": 0.0,
            "settledTotal": 0.0,
            "balance": 0.0,
            "notDue": 0.0, "days1to30": 0.0, "days31to60": 0.0, "days60plus": 0.0,
        })
        row["receivableTotal"] = _r(row["receivableTotal"] + e.amount)
        row["settledTotal"] = _r(row["settledTotal"] + e.settled_amount)
        row["balance"] = _r(row["balance"] + outstanding)
        row[_aging_bucket(e.due_date, today)] = _r(row[_aging_bucket(e.due_date, today)] + outstanding)
    rows = list(result.values())
    rows.sort(key=lambda r: r["balance"], reverse=True)
    return rows


# ============ 经营驾驶舱 ============

def executive_summary(db: Session) -> dict:
    receivables = db.query(FinanceEntry).filter(FinanceEntry.entry_type == ENTRY_RECEIVABLE).all()
    receivable_total = _r(sum(e.amount for e in receivables))
    received_total = _r(sum(e.settled_amount for e in receivables))
    outstanding_total = _r(sum(_outstanding(e) for e in receivables))

    today = date.today()
    overdue_total = _r(sum(
        _outstanding(e) for e in receivables
        if e.due_date and e.due_date < today and _outstanding(e) > 0
    ))

    order_count = db.query(SalesOrder).filter(SalesOrder.status != ORDER_CANCELLED).count()
    order_amount = _r(
        db.query(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .filter(SalesOrder.status != ORDER_CANCELLED).scalar()
    )

    return {
        "receivableTotal": receivable_total,
        "receivedTotal": received_total,
        "outstandingTotal": outstanding_total,
        "overdueTotal": overdue_total,
        "orderCount": order_count,
        "orderAmount": order_amount,
    }


def receivable_top(db: Session, limit: int = 5) -> list[dict]:
    rows = receivable_aging(db)[:limit]
    return [{"partnerName": r["partnerName"], "balance": r["balance"], "overdue": _r(
        r["days1to30"] + r["days31to60"] + r["days60plus"])} for r in rows]


def aging_distribution(db: Session) -> dict:
    rows = receivable_aging(db)
    return {
        "notDue": _r(sum(r["notDue"] for r in rows)),
        "days1to30": _r(sum(r["days1to30"] for r in rows)),
        "days31to60": _r(sum(r["days31to60"] for r in rows)),
        "days60plus": _r(sum(r["days60plus"] for r in rows)),
    }


def trends(db: Session, days: int = 30) -> list[dict]:
    """订单金额(按下单日)与回款金额(按发生日)趋势。"""
    today = date.today()
    start = today - timedelta(days=days - 1)

    order_rows = (
        db.query(SalesOrder)
        .filter(SalesOrder.status != ORDER_CANCELLED, SalesOrder.created_at >= datetime.combine(start, datetime.min.time()))
        .all()
    )
    order_by_day: dict[str, float] = {}
    for o in order_rows:
        key = o.created_at.date().isoformat()
        order_by_day[key] = _r(order_by_day.get(key, 0) + o.total_amount)

    receipt_rows = (
        db.query(FinanceEntry)
        .filter(FinanceEntry.entry_type == ENTRY_RECEIPT, FinanceEntry.occurred_date >= start)
        .all()
    )
    receipt_by_day: dict[str, float] = {}
    for e in receipt_rows:
        key = e.occurred_date.isoformat()
        receipt_by_day[key] = _r(receipt_by_day.get(key, 0) + e.amount)

    series = []
    for i in range(days):
        day = (start + timedelta(days=i)).isoformat()
        series.append({
            "date": day,
            "orderAmount": _r(order_by_day.get(day, 0)),
            "receiptAmount": _r(receipt_by_day.get(day, 0)),
        })
    return series


# ============ 保护性操作 ============

def delete_receivable(db: Session, entry_id: int) -> None:
    """删除应收流水(已有核销记录时禁止删除)。"""
    entry = db.query(FinanceEntry).filter(FinanceEntry.id == entry_id).first()
    if not entry:
        raise BusinessError("应收流水不存在", 404)
    settled_count = (
        db.query(FinanceSettlement)
        .filter(FinanceSettlement.target_entry_id == entry_id)
        .count()
    )
    if settled_count > 0:
        raise BusinessError("该应收已存在核销记录,不允许删除")
    db.delete(entry)
    db.commit()
