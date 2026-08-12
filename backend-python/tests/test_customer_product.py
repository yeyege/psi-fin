"""客户管理 + 商品 FNSKU/箱规 单元测试（MVP M1+M2）

覆盖：
- 客户：创建（分层校验/编码唯一）/ 关键词筛选 / 软删除 / 更新
- 商品：FNSKU 与箱规字段的创建与更新
"""
from app.common.errors import BusinessError
from app.models import Customer, Product
from app.services import customer_service
from app.schemas import CustomerCreate, CustomerUpdate


def _customer_payload(**overrides) -> CustomerCreate:
    base = dict(code="CUST-T1", name="测试客户", tier="B", contact="张三", phone="13800000000")
    base.update(overrides)
    return CustomerCreate(**base)


# ============ 客户管理 ============

def test_create_customer(db_session):
    c = customer_service.create_customer(db_session, _customer_payload())
    assert c.code == "CUST-T1"
    assert c.tier == "B"
    assert c.status == "ACTIVE"
    assert db_session.query(Customer).filter(Customer.code == "CUST-T1").count() == 1


def test_create_customer_duplicate_code_rejected(db_session):
    customer_service.create_customer(db_session, _customer_payload())
    try:
        customer_service.create_customer(db_session, _customer_payload(name="另一个客户"))
        assert False, "重复客户编码应报错"
    except BusinessError as e:
        assert "已存在" in e.message


def test_create_customer_invalid_tier(db_session):
    try:
        _customer_payload(tier="X")
        assert False, "非法分层应被 Schema 拒绝"
    except Exception:
        pass


def test_list_customers_keyword_filter(db_session):
    customer_service.create_customer(db_session, _customer_payload(code="CUST-A", name="领星客户"))
    customer_service.create_customer(db_session, _customer_payload(code="CUST-B", name="湾区客户"))
    result = customer_service.list_customers(db_session, keyword="湾区")
    assert result["total"] == 1
    assert result["list"][0].code == "CUST-B"

    result = customer_service.list_customers(db_session, keyword="CUST-A")
    assert result["total"] == 1
    assert result["list"][0].name == "领星客户"


def test_update_customer(db_session):
    c = customer_service.create_customer(db_session, _customer_payload())
    updated = customer_service.update_customer(
        db_session, c.id, CustomerUpdate(name="升级客户", tier="A", contact=None, phone=None)
    )
    assert updated.tier == "A"
    assert updated.name == "升级客户"
    assert updated.contact is None


def test_delete_customer_soft_delete(db_session):
    c = customer_service.create_customer(db_session, _customer_payload())
    customer_service.delete_customer(db_session, c.id)
    db_session.expire_all()
    deleted = db_session.get(Customer, c.id)
    assert deleted.status == "INACTIVE"


def test_get_customer_not_found(db_session):
    try:
        customer_service.get_customer(db_session, 999)
        assert False, "不存在的客户应报 404"
    except BusinessError as e:
        assert e.status == 404


# ============ 商品 FNSKU / 箱规 ============

def test_create_product_with_fns_ku_and_case_qty(db_session):
    from app.schemas import ProductCreate
    p = Product(
        name="带FNSKU商品", sku="SKU-F1", fns_ku="X0000TEST1", case_qty=24, unit="个",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    assert p.fns_ku == "X0000TEST1"
    assert p.case_qty == 24


def test_product_payload_camel_case_mapping():
    """前端 camelCase（fnsKu/caseQty）应正确映射到后端字段。"""
    from app.schemas import ProductCreate
    data = ProductCreate(
        name="商品", sku="SKU-C", fnsKu="X0000CAMEL", caseQty=50, unit="个",
    )
    assert data.fns_ku == "X0000CAMEL"
    assert data.case_qty == 50
