"""
============================================
 候选人需要实现以下接口：
============================================

POST /api/inbound-orders   — 创建入库单（任务1）
GET  /api/inventory         — 库存查询（任务2）

提示：
- 参考 routers/products.py 的实现风格
- 使用 SQLAlchemy 进行数据库操作
- 入库单创建需要使用事务（db.commit / db.rollback）
- 库存查询需要 JOIN 多表获取商品名、仓库名
- 注意 SQL 注入防护（使用参数化查询）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InboundOrderCreate

router = APIRouter(tags=["库存 & 入库"])


@router.post("/api/inbound-orders", status_code=201)
def create_inbound_order(req: InboundOrderCreate, db: Session = Depends(get_db)):
    """
    创建入库单 — 候选人实现

    要求：
    1. 生成入库单号 IN-YYYYMMDD-XXX
    2. 校验商品和库位是否存在
    3. 在事务中同时创建入库单 + 更新库存
    """
    # TODO: 候选人实现
    raise HTTPException(status_code=501, detail="请实现入库单创建功能（任务1）")


@router.get("/api/inventory")
def query_inventory(
    keyword: str | None = Query(default=None, description="商品名称/SKU 模糊搜索"),
    warehouse_id: int | None = Query(default=None, description="仓库ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    库存查询 — 候选人实现

    要求：
    1. 支持按 keyword 模糊搜索（商品名称/SKU）
    2. 支持按 warehouse_id 筛选
    3. 支持分页
    4. 返回关联的商品名称、SKU、仓库名称
    """
    # TODO: 候选人实现
    raise HTTPException(status_code=501, detail="请实现库存查询功能（任务2）")
