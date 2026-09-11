"""业财一体测试 — 销售订单状态机 / 发货生成应收 / 核销与账龄 / 驾驶舱口径

覆盖 openspec/changes/add-business-finance 的关键规则:
- 发货才生成应收,且幂等(唯一约束兜底)
- 部分核销与结清、预收余额复用、单张超额拦截
- 账龄以到期日为基准分段
- 驾驶舱金额与财务流水同源
"""
from datetime import date, timedelta

import pytest

from app.common.errors import BusinessError
from app.models import FinanceEntry, FinanceSettlement
from app.schemas import (
    SalesOrderCreate, SalesOrderItemRequest, SalesOrderUpdate,
    ReceiptCreate, SettlementAllocation,
)
from app.services import finance_service


# ============ 辅助 ============

def _order_req(credit_days=0, qty=2, price=100.0, product_id=1):
    return SalesOrderCreate(
        customerId=1,
        creditDays=credit_days,
        items=[SalesOrderItemRequest(productId=product_id, quantity=qty, unitPrice=price)],
    )


def _confirmed_order(db, credit_days=0, qty=2, price=100.0):
    order = finance_service.create_sales_order(db, _order_req(credit_days, qty, price))
    finance_service.confirm_sales_order(db, order.id)
    return order


def _receivables(db):
    return db.query(FinanceEntry).filter(FinanceEntry.entry_type == "RECEIVABLE").all()


# ============ 销售订单 ============

def test_create_order_amount_is_sum_of_items(db_session):
    req = SalesOrderCreate(customerId=1, creditDays=30, items=[
        SalesOrderItemRequest(productId=1, quantity=2, unitPrice=10.5),
        SalesOrderItemRequest(productId=2, quantity=3, unitPrice=20.0),
    ])
    order = finance_service.create_sales_order(db_session, req)

    assert order.order_no.startswith("SO-")
    assert order.status == finance_service.ORDER_DRAFT
    assert order.total_amount == pytest.approx(81.0)  # 2*10.5 + 3*20
    # 未发货:不得有应收
    assert _receivables(db_session) == []


def test_create_order_rejects_unknown_customer(db_session):
    req = SalesOrderCreate(customerId=999, items=[
        SalesOrderItemRequest(productId=1, quantity=1, unitPrice=1.0)])
    with pytest.raises(BusinessError):
        finance_service.create_sales_order(db_session, req)


def test_update_order_recalculates_amount_only_in_draft(db_session):
    order = finance_service.create_sales_order(db_session, _order_req(qty=2, price=100.0))
    updated = finance_service.update_sales_order(db_session, order.id, SalesOrderUpdate(
        items=[SalesOrderItemRequest(productId=1, quantity=5, unitPrice=100.0)]))
    assert updated.total_amount == pytest.approx(500.0)

    finance_service.confirm_sales_order(db_session, order.id)
    with pytest.raises(BusinessError):
        finance_service.update_sales_order(db_session, order.id, SalesOrderUpdate(
            items=[SalesOrderItemRequest(productId=1, quantity=1, unitPrice=1.0)]))


def test_state_machine_guards(db_session):
    order = finance_service.create_sales_order(db_session, _order_req())
    # 未确认不能发货
    with pytest.raises(BusinessError):
        finance_service.ship_sales_order(db_session, order.id)
    # 未发货不能完成
    finance_service.confirm_sales_order(db_session, order.id)
    with pytest.raises(BusinessError):
        finance_service.complete_sales_order(db_session, order.id)
    finance_service.ship_sales_order(db_session, order.id)
    # 已发货不能作废
    with pytest.raises(BusinessError):
        finance_service.cancel_sales_order(db_session, order.id)
    assert finance_service.complete_sales_order(db_session, order.id).status == "COMPLETED"


# ============ 发货生成应收(幂等) ============

def test_ship_generates_receivable_with_due_date(db_session):
    order = _confirmed_order(db_session, credit_days=30, qty=2, price=100.0)
    shipped = finance_service.ship_sales_order(db_session, order.id)

    assert shipped.status == finance_service.ORDER_SHIPPED
    assert shipped.shipped_at is not None

    entries = _receivables(db_session)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.amount == pytest.approx(200.0)
    assert entry.source_order_no == order.order_no
    assert entry.status == finance_service.ENTRY_OPEN
    assert entry.settled_amount == 0
    assert entry.due_date == shipped.shipped_at.date() + timedelta(days=30)


def test_receivable_generation_is_idempotent(db_session):
    order = _confirmed_order(db_session, credit_days=0)
    finance_service.ship_sales_order(db_session, order.id)
    assert len(_receivables(db_session)) == 1

    # 重复调用生成入口:不应新增
    finance_service.generate_receivable_for_order(db_session, order)
    assert len(_receivables(db_session)) == 1

    # 重复发货:应报错且不新增
    with pytest.raises(BusinessError):
        finance_service.ship_sales_order(db_session, order.id)
    assert len(_receivables(db_session)) == 1


# ============ 核销 ============

def test_partial_then_full_settlement(db_session):
    order = _confirmed_order(db_session, qty=1, price=1000.0)
    finance_service.ship_sales_order(db_session, order.id)
    entry = _receivables(db_session)[0]

    finance_service.register_receipt(db_session, ReceiptCreate(
        partnerName="测试客户", amount=600,
        allocations=[SettlementAllocation(targetEntryId=entry.id, amount=600)]))

    db_session.refresh(entry)
    assert entry.status == finance_service.ENTRY_PARTIAL
    assert entry.settled_amount == pytest.approx(600.0)
    assert finance_service._outstanding(entry) == pytest.approx(400.0)

    finance_service.register_receipt(db_session, ReceiptCreate(
        partnerName="测试客户", amount=400,
        allocations=[SettlementAllocation(targetEntryId=entry.id, amount=400)]))
    db_session.refresh(entry)
    assert entry.status == finance_service.ENTRY_SETTLED
    assert finance_service._outstanding(entry) == pytest.approx(0.0)


def test_prepayment_balance_can_be_reused(db_session):
    """收款 1000 仅核销 600,剩余 400 可再核销到另一张应收(预收余额复用)。"""
    order1 = _confirmed_order(db_session, qty=1, price=600.0)
    order2 = _confirmed_order(db_session, qty=1, price=400.0)
    finance_service.ship_sales_order(db_session, order1.id)
    finance_service.ship_sales_order(db_session, order2.id)
    e1, e2 = _receivables(db_session)

    receipt = finance_service.register_receipt(db_session, ReceiptCreate(
        partnerName="测试客户", amount=1000,
        allocations=[SettlementAllocation(targetEntryId=e1.id, amount=600)]))
    db_session.refresh(receipt)
    assert receipt.settled_amount == pytest.approx(600.0)
    assert finance_service._outstanding(receipt) == pytest.approx(400.0)

    # 用预收余额核销第二张应收
    finance_service.allocate_receipt(db_session, receipt.id, [
        SettlementAllocation(targetEntryId=e2.id, amount=400)])
    db_session.refresh(receipt)
    db_session.refresh(e2)
    assert finance_service._outstanding(receipt) == pytest.approx(0.0)
    assert e2.status == finance_service.ENTRY_SETTLED


def test_over_settlement_rejected_without_side_effects(db_session):
    order = _confirmed_order(db_session, qty=1, price=400.0)
    finance_service.ship_sales_order(db_session, order.id)
    entry = _receivables(db_session)[0]

    with pytest.raises(BusinessError):
        finance_service.register_receipt(db_session, ReceiptCreate(
            partnerName="测试客户", amount=500,
            allocations=[SettlementAllocation(targetEntryId=entry.id, amount=500)]))

    db_session.refresh(entry)
    assert entry.settled_amount == 0
    assert entry.status == finance_service.ENTRY_OPEN
    assert db_session.query(FinanceSettlement).count() == 0
    # 超额核销的那笔收款也不应落库(整单回滚)
    assert db_session.query(FinanceEntry).filter(
        FinanceEntry.entry_type == "RECEIPT").count() == 0


# ============ 账龄 / 驾驶舱 ============

def test_aging_buckets_by_due_date(db_session):
    today = date.today()
    rows = [
        ("AR-N1", today + timedelta(days=5), 100.0),   # 未到期
        ("AR-N2", today - timedelta(days=10), 200.0),  # 逾期1-30
        ("AR-N3", today - timedelta(days=45), 300.0),  # 逾期31-60
        ("AR-N4", today - timedelta(days=90), 400.0),  # 逾期60+
    ]
    for no, due, amount in rows:
        db_session.add(FinanceEntry(
            entry_no=no, entry_type="RECEIVABLE", partner_type="CUSTOMER",
            partner_name="账龄客户", amount=amount, settled_amount=0,
            occurred_date=today, due_date=due, status="OPEN"))
    db_session.commit()

    aging = {r["partnerName"]: r for r in finance_service.receivable_aging(db_session)}
    row = aging["账龄客户"]
    assert row["notDue"] == pytest.approx(100.0)
    assert row["days1to30"] == pytest.approx(200.0)
    assert row["days31to60"] == pytest.approx(300.0)
    assert row["days60plus"] == pytest.approx(400.0)
    assert row["balance"] == pytest.approx(1000.0)

    dist = finance_service.aging_distribution(db_session)
    assert sum(dist.values()) == pytest.approx(1000.0)


def test_executive_summary_matches_finance_entries(db_session):
    order = _confirmed_order(db_session, qty=1, price=1000.0)
    finance_service.ship_sales_order(db_session, order.id)
    entry = _receivables(db_session)[0]
    finance_service.register_receipt(db_session, ReceiptCreate(
        partnerName="测试客户", amount=300,
        allocations=[SettlementAllocation(targetEntryId=entry.id, amount=300)]))

    summary = finance_service.executive_summary(db_session)
    entries = _receivables(db_session)
    assert summary["receivableTotal"] == pytest.approx(sum(e.amount for e in entries))
    assert summary["receivedTotal"] == pytest.approx(sum(e.settled_amount for e in entries))
    assert summary["outstandingTotal"] == pytest.approx(
        sum(finance_service._outstanding(e) for e in entries))
    assert summary["outstandingTotal"] == pytest.approx(700.0)
    assert summary["orderCount"] == 1
    assert summary["orderAmount"] == pytest.approx(1000.0)


def test_delete_receivable_blocked_after_settlement(db_session):
    order = _confirmed_order(db_session, qty=1, price=100.0)
    finance_service.ship_sales_order(db_session, order.id)
    entry = _receivables(db_session)[0]

    # 未核销可删除
    finance_service.delete_receivable(db_session, entry.id)
    assert _receivables(db_session) == []


# ============ API 全链路冒烟 ============

def _login(c, username="admin", password="admin123") -> dict:
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}


def test_api_sales_order_to_receipt_chain(client):
    c, Session = client
    s = Session()
    from app.models import Customer, Product
    s.add(Customer(code="C-API", name="API客户", tier="A"))
    s.add(Product(name="API商品", sku="API-001", unit="个"))
    s.commit()
    s.close()

    headers = _login(c)

    # 建单
    r = c.post("/api/sales-orders", headers=headers, json={
        "customerId": 1, "creditDays": 30,
        "items": [{"productId": 1, "quantity": 3, "unitPrice": 50}],
    })
    assert r.status_code == 201, r.text
    order = r.json()["data"]
    assert order["totalAmount"] == pytest.approx(150.0)

    # 确认 + 发货
    assert c.post(f"/api/sales-orders/{order['id']}/confirm", headers=headers).status_code == 200
    r = c.post(f"/api/sales-orders/{order['id']}/ship", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "SHIPPED"

    # 应收已生成
    r = c.get("/api/finance/receivables", headers=headers)
    entries = r.json()["data"]["list"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["amount"] == pytest.approx(150.0)
    assert entry["dueDate"] == (date.today() + timedelta(days=30)).isoformat()

    # 部分收款核销
    r = c.post("/api/finance/receipts", headers=headers, json={
        "partnerName": "API客户", "amount": 50,
        "allocations": [{"targetEntryId": entry["id"], "amount": 50}],
    })
    assert r.status_code == 201, r.text

    # 驾驶舱口径
    r = c.get("/api/executive/summary", headers=headers)
    summary = r.json()["data"]
    assert summary["receivedTotal"] == pytest.approx(50.0)
    assert summary["outstandingTotal"] == pytest.approx(100.0)
