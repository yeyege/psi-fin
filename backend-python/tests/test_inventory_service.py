"""库存查询 Service 层单元测试 — 任务2

覆盖：keyword 模糊搜索、仓库筛选、分页、响应字段命名。

注意：使用与 conftest 种子数据不冲突的 ID（10+），避免唯一约束冲突。
"""
from app.models import Inventory, Product, Warehouse, Location
from app.services import inventory_service


def _setup_full(db_session):
    db_session.add_all([
        Warehouse(id=10, code="WH-A", name="广州主仓"),
        Warehouse(id=11, code="WH-B", name="深圳保税仓"),
        Location(id=10, warehouse_id=10, code="A-01"),
        Location(id=11, warehouse_id=10, code="A-02"),
        Location(id=12, warehouse_id=11, code="B-01"),
        Product(id=10, name="蓝牙耳机", sku="SKU-001"),
        Product(id=11, name="数据线", sku="SKU-002"),
        Product(id=12, name="手机壳", sku="SKU-003"),
        Inventory(product_id=10, location_code="A-01", quantity=100),
        Inventory(product_id=10, location_code="B-01", quantity=5),
        Inventory(product_id=11, location_code="A-02", quantity=50),
        Inventory(product_id=12, location_code="A-01", quantity=8),
    ])
    db_session.commit()


def test_query_inventory_keyword_filter(db_session):
    _setup_full(db_session)
    # 按商品名模糊搜索：蓝牙耳机 在 A-01、B-01 两条
    res = inventory_service.query_inventory(db_session, keyword="耳机")
    assert res["total"] == 2
    assert all("耳机" in r["productName"] for r in res["list"])

    # 按 SKU 模糊搜索
    res = inventory_service.query_inventory(db_session, keyword="SKU-002")
    assert res["total"] == 1
    assert res["list"][0]["sku"] == "SKU-002"


def test_query_inventory_warehouse_filter(db_session):
    _setup_full(db_session)
    res = inventory_service.query_inventory(db_session, warehouse_id=11)
    assert res["total"] == 1
    assert res["list"][0]["warehouseName"] == "深圳保税仓"
    assert res["list"][0]["locationCode"] == "B-01"


def test_query_inventory_pagination(db_session):
    _setup_full(db_session)
    page1 = inventory_service.query_inventory(db_session, page=1, page_size=2)
    assert page1["total"] == 4
    assert len(page1["list"]) == 2
    page2 = inventory_service.query_inventory(db_session, page=2, page_size=2)
    assert len(page2["list"]) == 2
    # 两页数据不重叠（用 productId+locationCode 复合键判断，因同库位可有多个商品）
    keys_p1 = {(r["productId"], r["locationCode"]) for r in page1["list"]}
    keys_p2 = {(r["productId"], r["locationCode"]) for r in page2["list"]}
    assert keys_p1.isdisjoint(keys_p2)
    assert len(keys_p1) == 2 and len(keys_p2) == 2


def test_query_inventory_returns_camel_case_fields(db_session):
    _setup_full(db_session)
    res = inventory_service.query_inventory(db_session, page=1, page_size=10)
    item = res["list"][0]
    # 响应字段为 camelCase，与前端接口约定一致
    for key in ("productId", "productName", "sku", "locationCode",
                "warehouseName", "quantity", "updatedAt"):
        assert key in item, f"missing field: {key}"
