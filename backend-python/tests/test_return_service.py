"""退货单 Service 单元测试（MVP M4）

覆盖：
- 创建（PENDING，不改变库存）/ 客户商品库位校验
- 收货：RESELL/RELABEL 转正品累加库存 + RETURN_IN 流水；SCRAP 只登记不累加
- 状态机：重复收货拒绝 / 未收货不可完成
- 单号递增（RT 前缀）
"""
from app.common.errors import BusinessError
from app.models import ReturnOrder, Inventory, InventoryFlow, Customer, Batch
from app.services import return_service
from app.schemas import ReturnOrderCreate, ReturnItemRequest


def _mk_return(db, *, items=None, customer_id=1, source="FBA") -> ReturnOrder:
    data = ReturnOrderCreate(
        customer_id=customer_id,
        source=source,
        items=items or [
            ReturnItemRequest(product_id=1, quantity=20, location_code="LOC-01", disposition="RESELL"),
        ],
    )
    return return_service.create_return_order(db, data)


def _mk_customer(db, code="CUST-R", name="退货客户"):
    c = Customer(code=code, name=name, tier="A")
    db.add(c)
    db.flush()
    return c


def test_create_return_order_pending_no_stock_change(db_session):
    order = _mk_return(db_session)
    assert order.status == "PENDING"
    assert order.order_no.startswith("RT-")
    assert db_session.query(Inventory).count() == 0  # 创建不触碰库存


def test_create_return_order_invalid_customer(db_session):
    try:
        _mk_return(db_session, customer_id=999)
        assert False, "客户不存在应报 404"
    except BusinessError as e:
        assert e.status == 404


def test_receive_resell_adds_stock_and_flow(db_session):
    order = _mk_return(db_session)
    received = return_service.receive_return_order(db_session, order.id)
    assert received.status == "RECEIVED"

    inv = db_session.query(Inventory).filter_by(product_id=1).one()
    assert inv.available_qty == 20

    flows = db_session.query(InventoryFlow).all()
    assert len(flows) == 1
    assert flows[0].flow_type == "RETURN_IN"
    assert flows[0].order_type == "RETURN"
    assert flows[0].order_no == order.order_no
    assert db_session.query(Batch).count() == 1


def test_receive_scrap_only_registers_no_stock(db_session):
    order = _mk_return(db_session, items=[
        ReturnItemRequest(product_id=1, quantity=30, location_code="LOC-01", disposition="SCRAP"),
    ])
    received = return_service.receive_return_order(db_session, order.id)
    assert received.status == "RECEIVED"
    assert db_session.query(Inventory).count() == 0  # 报废不累加库存
    assert db_session.query(Batch).count() == 0
    assert db_session.query(InventoryFlow).count() == 0


def test_receive_mixed_dispositions(db_session):
    """混合作业：RESELL 加库存、RELABEL 加库存、SCRAP 只登记。"""
    order = _mk_return(db_session, items=[
        ReturnItemRequest(product_id=1, quantity=10, location_code="LOC-01", disposition="RESELL"),
        ReturnItemRequest(product_id=2, quantity=5, location_code="LOC-02", disposition="RELABEL"),
        ReturnItemRequest(product_id=1, quantity=3, location_code="LOC-01", disposition="SCRAP"),
    ])
    return_service.receive_return_order(db_session, order.id)
    invs = db_session.query(Inventory).all()
    assert len(invs) == 2
    assert db_session.query(InventoryFlow).count() == 2
    assert db_session.query(Batch).count() == 2


def test_receive_twice_rejected(db_session):
    order = _mk_return(db_session)
    return_service.receive_return_order(db_session, order.id)
    try:
        return_service.receive_return_order(db_session, order.id)
        assert False, "重复收货应报错"
    except BusinessError as e:
        assert "不允许收货" in e.message


def test_finish_requires_received(db_session):
    order = _mk_return(db_session)
    try:
        return_service.finish_return_order(db_session, order.id)
        assert False, "未收货不可完成处理"
    except BusinessError as e:
        assert "不允许完成" in e.message

    return_service.receive_return_order(db_session, order.id)
    done = return_service.finish_return_order(db_session, order.id)
    assert done.status == "DONE"


def test_return_order_no_increments(db_session):
    o1 = _mk_return(db_session)
    o2 = _mk_return(db_session, items=[
        ReturnItemRequest(product_id=2, quantity=1, location_code="LOC-02", disposition="SCRAP"),
    ])
    assert o1.order_no != o2.order_no
    assert o2.order_no > o1.order_no
