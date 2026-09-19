"""会计内核模型 — 科目表(COA) + 记账凭证 + 会计期间

见 openspec/changes/oss-finance-ai-platform/specs/finance/accounting-core/spec.md

- Account    会计科目:树状结构,仅明细科目(is_leaf)可挂分录;支持辅助核算维度
- Voucher    记账凭证:状态机 DRAFT → POSTED → REVERSED;过账后不可改删,更正是红字冲销
- VoucherLine 凭证分录:借/贷方向,金额允许为负(红字),可挂辅助核算维度(客户/供应商/仓库)
- Period     会计期间:自然月,OPEN/CLOSED;closed 期间拒绝凭证写入

设计要点(见 design.md D3/D4):
- 冲销凭证通过 reverses_voucher_no 指向被冲销原凭证,原凭证以 reversed_voucher_no 回指,双向关联
- 金额字段沿用项目口径 Float + 服务层 round(...,2)(管理会计演示口径)
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Index, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ============ 枚举常量(字符串存储,与单据状态机风格一致) ============

# 科目类别
CAT_ASSET = "ASSET"        # 资产
CAT_LIABILITY = "LIABILITY"  # 负债
CAT_EQUITY = "EQUITY"      # 权益
CAT_REVENUE = "REVENUE"    # 收入
CAT_EXPENSE = "EXPENSE"    # 费用
ACCOUNT_CATEGORIES = (CAT_ASSET, CAT_LIABILITY, CAT_EQUITY, CAT_REVENUE, CAT_EXPENSE)

# 科目余额方向
DIR_DEBIT = "DEBIT"        # 借
DIR_CREDIT = "CREDIT"      # 贷
BALANCE_DIRECTIONS = (DIR_DEBIT, DIR_CREDIT)

# 分录方向
LINE_DEBIT = "D"
LINE_CREDIT = "C"
LINE_DIRECTIONS = (LINE_DEBIT, LINE_CREDIT)

# 辅助核算维度(逗号分隔存储,空串表示不启用)
AUX_TYPES = ("CUSTOMER", "SUPPLIER", "WAREHOUSE")

# 凭证状态机
VOUCHER_DRAFT = "DRAFT"
VOUCHER_POSTED = "POSTED"
VOUCHER_REVERSED = "REVERSED"

# 凭证来源
SOURCE_MANUAL = "MANUAL"   # 手工录入
SOURCE_ENGINE = "ENGINE"   # 凭证引擎自动生成(2.3)
SOURCE_AI = "AI_DRAFT"     # AI 草稿确认后生成(Phase 3)

# 期间状态
PERIOD_OPEN = "OPEN"
PERIOD_CLOSED = "CLOSED"


class Account(Base):
    """会计科目 — 树状 COA

    - parent_id 自关联;顶级科目 parent_id 为 NULL
    - is_leaf 明细科目标记:新增子科目时由服务层自动置 False,仅明细科目可挂分录
    - aux_dimensions 辅助核算维度,逗号分隔(如 "CUSTOMER"),空串表示不启用
    """
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_category", "category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)      # ASSET / LIABILITY / EQUITY / REVENUE / EXPENSE
    direction = Column(String(10), nullable=False)     # DEBIT / CREDIT 余额方向
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    level = Column(Integer, nullable=False, default=1)  # 层级,顶级=1
    is_leaf = Column(Boolean, nullable=False, default=True)
    aux_dimensions = Column(String(100), nullable=False, default="")
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE / INACTIVE
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    parent = relationship("Account", remote_side=[id], back_populates="children")
    children = relationship("Account", back_populates="parent", order_by="Account.code")

    def aux_list(self) -> list:
        return [d for d in (self.aux_dimensions or "").split(",") if d]


class Period(Base):
    """会计期间 — 自然月,code 形如 2026-09"""
    __tablename__ = "accounting_periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(7), nullable=False, unique=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default=PERIOD_OPEN)  # OPEN / CLOSED
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Voucher(Base):
    """记账凭证 — 状态机 DRAFT → POSTED → REVERSED,过账后不可变

    红字冲销:新凭证 reverses_voucher_no 指向原凭证,原凭证 reversed_voucher_no 回指,
    原凭证状态置 REVERSED;冲销凭证本身直接为 POSTED。
    """
    __tablename__ = "vouchers"
    __table_args__ = (
        Index("ix_vouchers_period_status", "period_code", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_no = Column(String(50), nullable=False, unique=True, index=True)  # JV-YYYYMMDD-XXX
    voucher_date = Column(Date, nullable=False)
    period_code = Column(String(7), nullable=False, index=True)  # 冗余:期间聚合免换算
    status = Column(String(20), nullable=False, default=VOUCHER_DRAFT)
    source_type = Column(String(20), nullable=False, default=SOURCE_MANUAL)
    memo = Column(String(200), nullable=False, default="")
    reverses_voucher_no = Column(String(50), nullable=True)   # 本凭证冲销了哪张原凭证
    reversed_voucher_no = Column(String(50), nullable=True)   # 本凭证被哪张红字凭证冲销
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    lines = relationship(
        "VoucherLine", back_populates="voucher",
        cascade="all, delete-orphan", order_by="VoucherLine.seq",
    )


class VoucherLine(Base):
    """凭证分录 — direction D 借 / C 贷;amount 允许为负(红字凭证)"""
    __tablename__ = "voucher_lines"
    __table_args__ = (
        UniqueConstraint("voucher_id", "seq", name="uk_voucher_line_seq"),
        Index("ix_voucher_lines_account", "account_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False)
    seq = Column(Integer, nullable=False)  # 分录行号,凭证内递增
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    direction = Column(String(1), nullable=False)  # D 借 / C 贷
    amount = Column(Float, nullable=False)         # 负数即红字
    aux_type = Column(String(20), nullable=True)   # CUSTOMER / SUPPLIER / WAREHOUSE
    aux_id = Column(Integer, nullable=True)
    aux_name = Column(String(200), nullable=True)  # 冗余留痕,主数据改名不失真
    memo = Column(String(200), nullable=True)

    voucher = relationship("Voucher", back_populates="lines")
    account = relationship("Account")
