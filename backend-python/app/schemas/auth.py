"""用户与登录 Schema（camelCase）"""
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel


class UserCreate(CamelModel):
    username: str = Field(min_length=2, max_length=64, description="登录名")
    password: str = Field(min_length=6, max_length=64, description="密码（≥6 位）")
    role: Literal["admin", "operator"] = "operator"


class UserUpdate(CamelModel):
    password: str | None = Field(default=None, min_length=6, max_length=64)
    role: Literal["admin", "operator"] | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None


class UserResponse(CamelModel):
    id: int
    username: str
    role: str
    status: str
    createdAt: datetime


class LoginRequest(CamelModel):
    username: str
    password: str


class LoginResponse(CamelModel):
    token: str
    user: UserResponse
