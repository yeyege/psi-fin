"""通用工具：业务异常、单号生成、分页信封"""
from app.common.errors import BusinessError
from app.common.order_no import generate_order_no
from app.common.pagination import page_result

__all__ = ["BusinessError", "generate_order_no", "page_result"]
