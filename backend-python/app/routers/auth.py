"""用户与鉴权 API — 登录 / 登出 / 当前用户 / 用户管理（admin）"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserCreate, UserUpdate, LoginRequest
from app.services import auth_service
from app.services.auth_service import get_current_user, require_admin
from app.models import User

router = APIRouter(tags=["用户与鉴权"])


# ---------- 登录 / 登出 / 当前用户 ----------
@router.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.login(db, req.username, req.password)
    return {"code": 200, "message": "登录成功", "data": result}


@router.post("/api/auth/logout")
def logout(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    """退出登录：使当前 token 失效（此后请求返回 401）。"""
    if authorization and authorization.startswith("Bearer "):
        auth_service.logout(db, authorization[len("Bearer "):].strip())
    return {"code": 200, "message": "退出成功", "data": None}


@router.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"code": 200, "message": "success",
            "data": auth_service._build_user_response(user)}


# ---------- 用户管理（仅 admin） ----------
@router.get("/api/users")
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = auth_service.list_users(db, page=page, page_size=page_size)
    return {"code": 200, "message": "success", "data": result}


@router.post("/api/users", status_code=201)
def create_user(req: UserCreate, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    user = auth_service.create_user(db, req)
    return {"code": 201, "message": "用户创建成功",
            "data": auth_service._build_user_response(user)}


@router.put("/api/users/{user_id}")
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    user = auth_service.update_user(db, user_id, req)
    return {"code": 200, "message": "用户更新成功",
            "data": auth_service._build_user_response(user)}


@router.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    auth_service.delete_user(db, user_id)
    return {"code": 200, "message": "用户删除成功", "data": None}
