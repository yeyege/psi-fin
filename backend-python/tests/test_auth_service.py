"""用户与鉴权单元测试 — 登录/登出/me、用户 CRUD、admin 角色隔离

对标领星WMS：未登录 401、非管理员 403、重复用户名 409、账号停用 403。
"""
import pytest

from app.common.errors import BusinessError
from app.models import User, AuthToken
from app.models.auth import ROLE_ADMIN, ROLE_OPERATOR, STATUS_ACTIVE, STATUS_INACTIVE
from app.schemas import UserCreate, UserUpdate, LoginRequest
from app.services import auth_service


def _create(db, username="op1", role="operator", password="pass123"):
    return auth_service.create_user(db, UserCreate(username=username, password=password, role=role))


def _login(db, username, password="pass123"):
    return auth_service.login(db, username, password)


# ---------- 密码哈希 ----------
def test_password_hash_is_salted_and_verifiable():
    h1 = auth_service.hash_password("pass123")
    h2 = auth_service.hash_password("pass123")
    assert h1 != h2  # 随机盐：相同密码两次哈希不同
    assert auth_service.verify_password("pass123", h1)
    assert not auth_service.verify_password("wrong", h1)
    assert not auth_service.verify_password("pass123", "not-a-hash")


# ---------- 登录 ----------
def test_login_success_returns_token_and_user(db_session):
    _create(db_session, username="admin2", role="admin")
    result = _login(db_session, "admin2")
    assert result["token"]
    assert result["user"]["username"] == "admin2"
    assert result["user"]["role"] == "admin"
    assert db_session.query(AuthToken).count() == 1


def test_login_wrong_password_rejected(db_session):
    _create(db_session, username="op2")
    with pytest.raises(BusinessError) as exc:
        _login(db_session, "op2", "wrongxx")
    assert exc.value.status == 401


def test_login_unknown_user_rejected(db_session):
    with pytest.raises(BusinessError) as exc:
        _login(db_session, "nobody")
    assert exc.value.status == 401


def test_login_inactive_user_rejected(db_session):
    user = _create(db_session, username="op3")
    auth_service.update_user(db_session, user.id, UserUpdate(status=STATUS_INACTIVE))
    with pytest.raises(BusinessError) as exc:
        _login(db_session, "op3")
    assert exc.value.status == 403


# ---------- get_user_by_token ----------
def test_token_validates_user(db_session):
    user = _create(db_session, username="op4")
    result = _login(db_session, "op4")
    got = auth_service.get_user_by_token(db_session, result["token"])
    assert got is not None and got.id == user.id


def test_invalid_or_expired_token_rejected(db_session):
    _create(db_session, username="op5")
    result = _login(db_session, "op5")
    assert auth_service.get_user_by_token(db_session, "bad-token") is None

    # 过期 token：直接改 expires_at 模拟
    from datetime import datetime, timedelta
    tok = db_session.query(AuthToken).first()
    tok.expires_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    assert auth_service.get_user_by_token(db_session, result["token"]) is None


def test_logout_invalidates_token(db_session):
    _create(db_session, username="op6")
    result = _login(db_session, "op6")
    auth_service.logout(db_session, result["token"])
    assert db_session.query(AuthToken).count() == 0
    assert auth_service.get_user_by_token(db_session, result["token"]) is None


# ---------- 用户 CRUD ----------
def test_create_user_duplicate_rejected(db_session):
    _create(db_session, username="dup")
    with pytest.raises(BusinessError) as exc:
        _create(db_session, username="dup")
    assert exc.value.status == 409


def test_update_user_reset_password_and_role(db_session):
    user = _create(db_session, username="op7")
    updated = auth_service.update_user(db_session, user.id, UserUpdate(password="newpass1", role=ROLE_ADMIN))
    assert updated.role == ROLE_ADMIN
    assert auth_service.verify_password("newpass1", updated.password_hash)
    # 旧密码失效、新密码可登录
    with pytest.raises(BusinessError):
        _login(db_session, "op7", "pass123")
    assert _login(db_session, "op7", "newpass1")["token"]


def test_delete_user_removes_tokens(db_session):
    user = _create(db_session, username="op8")
    result = _login(db_session, "op8")
    auth_service.delete_user(db_session, user.id)
    assert db_session.query(User).count() == 0
    assert db_session.query(AuthToken).count() == 0
    assert auth_service.get_user_by_token(db_session, result["token"]) is None


def test_delete_last_admin_rejected(db_session):
    _create(db_session, username="onlyadmin", role="admin")
    user = db_session.query(User).filter(User.username == "onlyadmin").first()
    with pytest.raises(BusinessError) as exc:
        auth_service.delete_user(db_session, user.id)
    assert exc.value.status == 409


def test_delete_unknown_user_rejected(db_session):
    with pytest.raises(BusinessError) as exc:
        auth_service.delete_user(db_session, 999)
    assert exc.value.status == 404


# ---------- 角色隔离 ----------
def test_get_current_user_returns_active_user(db_session):
    user = _create(db_session, username="op9")
    result = _login(db_session, "op9")
    got = auth_service.get_user_by_token(db_session, result["token"])
    assert got.id == user.id
