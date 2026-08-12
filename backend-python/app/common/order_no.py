"""单据号生成：{PREFIX}-YYYYMMDD-XXX，按日递增（各单据类型独立序列）

并发下单号可能冲突（唯一约束），由调用方在事务中捕获 IntegrityError 重试。
"""
import re
from datetime import datetime

from sqlalchemy import func


def generate_order_no(db, model, prefix: str, seq_len: int = 3,
                      no_col: str = "order_no") -> str:
    """按模型上的单号字段生成下一个单号。

    Args:
        db: SQLAlchemy Session
        model: 含单号唯一列的 ORM 模型
        prefix: 单号前缀，如 IN / OUT / WV / PK
        seq_len: 序号位数
        no_col: 单号列名（默认 order_no；波次 wave_no、拣货单 picking_no 等可指定）
    """
    today = datetime.now().strftime("%Y%m%d")
    like = f"{prefix}-{today}-%"
    col = getattr(model, no_col)
    # 先按字符串长度降序（同长度下字典序≈数值序），避免 "999" 大于 "1000" 的字符串排序陷阱
    last = (
        db.query(model)
        .filter(col.like(like))
        .order_by(func.length(col).desc(), col.desc())
        .first()
    )
    if last is None:
        return f"{prefix}-{today}-{1:0{seq_len}d}"
    # 解析末尾全部数字，避免固定截取 3 位导致 1000+ 序号回绕冲突
    match = re.search(r"(\d+)$", getattr(last, no_col))
    seq = int(match.group(1)) + 1 if match else 1
    return f"{prefix}-{today}-{seq:0{seq_len}d}"
