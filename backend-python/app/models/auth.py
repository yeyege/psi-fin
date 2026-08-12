"""用户与鉴权模型

- User      : 系统用户（admin 管理员 / operator 操作员），软禁用（status=INACTIVE）
- AuthToken : 登录签发的随机 token（可撤销、可过期）
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
STATUS_ACTIVE = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default=ROLE_OPERATOR)
    status = Column(String(16), nullable=False, default=STATUS_ACTIVE)
    created_at = Column(DateTime, default=datetime.now)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
