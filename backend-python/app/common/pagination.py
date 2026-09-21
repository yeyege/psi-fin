"""分页响应信封工具 — 统一 list/total/page/pageSize 结构。

此前 13 个 service 各自手写 `{"list":..., "total":..., "page":..., "pageSize":...}`，
字段名/结构靠复制维持一致，易漏改。收敛到本函数作为单一来源，
输出结构与前端契约保持完全一致（不改变响应字节）。
"""
from typing import Any


def page_result(items: list[Any], total: int, page: int, page_size: int) -> dict:
    """构造统一分页信封。"""
    return {"list": items, "total": total, "page": page, "pageSize": page_size}
