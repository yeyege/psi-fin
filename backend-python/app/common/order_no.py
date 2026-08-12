"""单据号生成：{PREFIX}-YYYYMMDD-XXX，按日递增（各单据类型独立序列）

并发下单号可能冲突（唯一约束），由调用方在事务中捕获 IntegrityError 重试。
"""
from datetime import datetime

from sqlalchemy import inspect


def generate_order_no(db, model, prefix: str, seq_len: int = 3) -> str:
    """按模型上的 order_no 字段生成下一个单号。

    Args:
        db: SQLAlchemy Session
        model: 含 order_no 唯一列的 ORM 模型
        prefix: 单号前缀，如 IN / OUT / MV / ADJ
    """
    today = datetime.now().strftime("%Y%m%d")
    like = f"{prefix}-{today}-%"
    last = (
        db.query(model)
        .filter(model.order_no.like(like))
        .order_by(model.order_no.desc())
        .first()
    )
    seq = int(last.order_no[-(seq_len):]) + 1 if last else 1
    return f"{prefix}-{today}-{seq:0{seq_len}d}"
