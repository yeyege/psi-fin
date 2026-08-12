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
