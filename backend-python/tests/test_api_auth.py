"""业务 API 鉴权测试 — 登录校验已全量挂载

对标领星WMS：
- 未登录访问任一业务 API → 401；
- 登录拿到 token 后 → 200；
- 操作员访问用户管理 → 403（仅 admin）。

client fixture 见 conftest.py（独立临时库 + admin 账号）。
"""
from fastapi.testclient import TestClient

from app.schemas import UserCreate
from app.services import auth_service


def _login(c: TestClient, username="admin", password="admin123") -> str:
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["data"]["token"]


def test_business_api_rejects_anonymous(client):
    c, _ = client
    assert c.get("/api/products").status_code == 401
    assert c.get("/api/inventory").status_code == 401
    assert c.get("/api/inbound-orders").status_code == 401
    assert c.get("/api/outbound-orders").status_code == 401
    assert c.get("/api/customers").status_code == 401
    assert c.get("/api/dashboard/summary").status_code == 401
    assert c.get("/api/waves").status_code == 401
    assert c.get("/api/returns").status_code == 401
    assert c.get("/api/warehouses").status_code == 401
    assert c.get("/api/transfers").status_code == 401
    assert c.get("/api/users").status_code == 401


def test_invalid_token_rejected(client):
    c, _ = client
    r = c.get("/api/products", headers={"Authorization": "Bearer bad-token"})
    assert r.status_code == 401


def test_business_api_ok_with_token(client):
    c, _ = client
    token = _login(c)
    h = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/products", headers=h).status_code == 200
    assert c.get("/api/inventory", headers=h).status_code == 200
    assert c.get("/api/customers", headers=h).status_code == 200


def test_operator_cannot_manage_users(client):
    c, Session = client
    s = Session()
    auth_service.create_user(
        s, UserCreate(username="op", password="op123456", role="operator"))
    s.close()

    token = _login(c, "op", "op123456")
    h = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/users", headers=h).status_code == 403  # 非管理员
    assert c.get("/api/products", headers=h).status_code == 200  # 业务接口可访问
