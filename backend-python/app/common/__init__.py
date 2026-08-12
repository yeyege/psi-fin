"""通用工具：业务异常、单号生成"""
from app.common.errors import BusinessError
from app.common.order_no import generate_order_no

__all__ = ["BusinessError", "generate_order_no"]
