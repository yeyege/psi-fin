"""API 契约测试 — 前后端 camelCase 契约 + 全局异常处理器

回归保障：
1. /api/products、/api/customers 挂 response_model 后，返回键为 camelCase
   （fnsKu / caseQty / createdAt），前端 FNSKU 列、箱规列不再显示 "-"/undefined；
2. 编辑商品提交 fnsKu 不再被置空（数据丢失回归）；
3. 全局 BusinessError 处理器：业务异常返回 JSON，body 含 detail/message/data。
"""
from fastapi.testclient import TestClient


def _login(c: TestClient, username="admin", password="admin123") -> str:
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["data"]["token"]


def _auth(c: TestClient) -> dict:
    return {"Authorization": f"Bearer {_login(c)}"}


def test_products_use_camelcase_keys(client):
    c, Session = client
    s = Session()
    from app.models import Product
    s.add(Product(name="合约商品", sku="CT-001", fns_ku="FN-ABC-123",
                  case_qty=12, unit="个"))
    s.commit()
    s.close()

    r = c.get("/api/products", headers=_auth(c))
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    item = body["data"]["list"][0]
    assert "fnsKu" in item, f"缺少 camelCase 键 fnsKu，实际键: {sorted(item)}"
    assert "caseQty" in item, f"缺少 camelCase 键 caseQty，实际键: {sorted(item)}"
    assert "createdAt" in item and "updatedAt" in item
    # 不得再输出 snake_case 键
    assert "fns_ku" not in item and "case_qty" not in item and "created_at" not in item
    assert item["fnsKu"] == "FN-ABC-123" and item["caseQty"] == 12


def test_customers_use_camelcase_keys(client):
    c, Session = client
    s = Session()
    from app.models import Customer
    s.add(Customer(code="C-1001", name="契约客户", tier="B"))
    s.commit()
    s.close()

    r = c.get("/api/customers", headers=_auth(c))
    assert r.status_code == 200
    item = r.json()["data"]["list"][0]
    assert "createdAt" in item, f"缺少 camelCase 键 createdAt，实际键: {sorted(item)}"
    assert item["tier"] == "B"
    assert "created_at" not in item


def test_update_product_preserves_fns_ku(client):
    """编辑商品时 fnsKu 不应被置空（修复前会把已有 FNSKU 覆盖为 null）。"""
    c, Session = client
    s = Session()
    from app.models import Product
    p = Product(name="原商品", sku="CT-002", fns_ku="FN-KEEP-1", unit="个")
    s.add(p)
    s.commit()
    pid = p.id
    s.close()

    h = _auth(c)
    r = c.put(f"/api/products/{pid}", json={"name": "改名商品"}, headers=h)
    assert r.status_code == 200
    item = r.json()["data"]
    assert item["fnsKu"] == "FN-KEEP-1", "更新时 fnsKu 不应被置空"
    assert item["name"] == "改名商品"


def test_business_error_returns_json_body(client):
    """全局 BusinessError 处理器：404 业务异常返回 JSON，而非空响应。"""
    c, _ = client
    r = c.get("/api/products/99999", headers=_auth(c))
    assert r.status_code == 404
    body = r.json()
    assert "detail" in body and "message" in body
    assert body["data"] is None
    assert body["message"] == "商品不存在"


def test_counts_camelcase_and_complete_flow(client):
    """盘点单 API：camelCase 契约 + 创建→提交→完成自动生成调整单全流程。"""
    from datetime import datetime

    from app.models import Batch, Inventory, Location, Product, Warehouse, Zone
    from app.services import inventory_service

    c, Session = client
    s = Session()
    s.add_all([
        Warehouse(id=1, code="WH-API", name="API仓"),
        Zone(id=1, warehouse_id=1, code="Z-GOODS", name="正品区"),
        Location(id=1, zone_id=1, warehouse_id=1, code="LOC-01", priority=5),
        Product(id=9, name="盘点商品", sku="CT-CNT-1", unit="个"),
    ])
    b = Batch(batch_no="CNT-B-1", product_id=9, inbound_date=datetime.now())
    s.add(b)
    s.flush()
    inventory_service.add_stock(
        s, product_id=9, location_code="LOC-01", batch_id=b.id, quantity=50,
        flow_type=inventory_service.FLOW_TYPE_INBOUND,
        order_type=inventory_service.ORDER_TYPE_INBOUND, order_no="API-SEED")
    s.commit()
    s.close()

    h = _auth(c)

    # 创建盘点单（按库位）
    r = c.post("/api/counts", json={"scopeType": "LOCATION", "scopeValue": "LOC-01",
                                    "remark": "API盘点"}, headers=h)
    assert r.status_code == 201
    count = r.json()["data"]
    assert "countNo" in count and count["countNo"].startswith("CC-")
    assert "scopeType" in count and "systemQty" in count["items"][0]
    assert "system_qty" not in count["items"][0]
    assert count["items"][0]["systemQty"] == 50
    count_id = count["id"]
    item_id = count["items"][0]["id"]

    # 录入实盘数量（差异 +10 → 自动盘盈）
    r = c.post(f"/api/counts/{count_id}/submit",
               json={"items": [{"itemId": item_id, "countedQty": 60}]}, headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["items"][0]["countedQty"] == 60

    # 完成盘点 → 自动生成调整单 + 流水
    r = c.post(f"/api/counts/{count_id}/complete", headers=h)
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["status"] == "COMPLETED"
    assert body["stats"]["accuracyRate"] == 0.0
    assert body["items"][0]["diffQty"] == 10

    s2 = Session()
    try:
        rows = s2.query(Inventory).filter_by(product_id=9, location_code="LOC-01").all()
        assert sum(x.available_qty for x in rows) == 60
    finally:
        s2.close()
