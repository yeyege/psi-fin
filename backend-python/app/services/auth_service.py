"""用户与鉴权服务 — 登录签发随机 token、用户 CRUD、鉴权依赖

对标领星WMS：
- 密码使用 PBKDF2-SHA256（标准库，100k 轮）+ 随机盐，不落明文；
- token 随机值入库（可撤销），登录有效期 7 天；
- 用户管理仅 admin 可见，operator 只能操作业务单据。
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.common.errors import BusinessError
from app.database import get_db
from app.models import User, AuthToken
from app.models.auth import ROLE_ADMIN, STATUS_ACTIVE, STATUS_INACTIVE

TOKEN_TTL_DAYS = 7
_PBKDF2_ITERATIONS = 100_000


# ---------- 密码哈希（标准库实现，不引入额外依赖） ----------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    calc = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(calc, digest)


# ---------- 用户 CRUD ----------
def _build_user_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "status": user.status,
        "createdAt": user.created_at,
    }


def create_user(db: Session, data) -> User:
    exists = db.query(User).filter(User.username == data.username).first()
    if exists:
        raise BusinessError(f"用户名已存在: {data.username}", 409)
    user = User(username=data.username, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, page: int = 1, page_size: int = 20) -> dict:
    query = db.query(User)
    total = query.count()
    rows = query.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"list": [_build_user_response(u) for u in rows], "total": total,
            "page": page, "pageSize": page_size}


def update_user(db: Session, user_id: int, data) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessError("用户不存在", 404)
    if data.password:
        user.password_hash = hash_password(data.password)
    if data.role:
        user.role = data.role
    if data.status:
        user.status = data.status
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessError("用户不存在", 404)
    admin_count = db.query(User).filter(User.role == ROLE_ADMIN, User.status == STATUS_ACTIVE).count()
    if user.role == ROLE_ADMIN and admin_count <= 1:
        raise BusinessError("不能删除最后一个启用管理员", 409)
    db.delete(user)
    db.query(AuthToken).filter(AuthToken.user_id == user_id).delete()
    db.commit()


# ---------- 登录 / 登出 / 鉴权 ----------
def login(db: Session, username: str, password: str) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise BusinessError("用户名或密码错误", 401)
    if user.status != STATUS_ACTIVE:
        raise BusinessError("账号已停用，请联系管理员", 403)
    token = AuthToken(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=datetime.now() + timedelta(days=TOKEN_TTL_DAYS),
    )
    db.add(token)
    db.commit()
    return {"token": token.token, "user": _build_user_response(user)}


def logout(db: Session, token_value: str) -> None:
    db.query(AuthToken).filter(AuthToken.token == token_value).delete()
    db.commit()


def get_user_by_token(db: Session, token_value: str) -> User | None:
    token = (
        db.query(AuthToken)
        .filter(AuthToken.token == token_value)
        .first()
    )
    if not token:
        return None
    if token.expires_at < datetime.now():
        db.delete(token)
        db.commit()
        return None
    return token.user


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """FastAPI 鉴权依赖：解析 `Authorization: Bearer <token>`，失败抛 401。

    依赖注入中的异常不会被 router 层 try/except 捕获，直接抛 HTTPException。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    token_value = authorization[len("Bearer "):].strip()
    user = get_user_by_token(db, token_value)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if user.status != STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="账号已停用")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """admin 专属接口依赖：非管理员拒绝。"""
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="无权限：仅管理员可操作")
    return user
