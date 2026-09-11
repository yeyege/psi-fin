from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.errors import BusinessError
from app.database import engine, Base
from app.routers import (
    products, warehouses, inbound, outbound, inventory, transfers, customers,
    dashboard, returns, waves, auth, counts,
    sales_orders, finance, executive,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 初始化示例数据（仅当库为空时）。"""
    Base.metadata.create_all(bind=engine)
    from init_data import init_data, init_admin
    init_data()
    init_admin()
    yield


app = FastAPI(
    title="进销存 + 业财一体中后台 API",
    description="进销存与业财一体化中后台 API（库存底座对标领星WMS：批次库存 / 可用+锁定 / 全量流水 / 单据状态机；业财层：销售订单 → 发货生成应收 → 收款核销 → 经营驾驶舱）",
    version="3.0.0",
    lifespan=lifespan,
)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """业务异常统一转 JSON 响应（与 router 层抛 HTTPException 的响应体保持一致）。"""
    return JSONResponse(
        status_code=exc.status,
        content={"detail": exc.message, "message": exc.message, "data": None},
    )


# CORS（前端经 vite/nginx 代理同源访问，无 cookie 场景，无需 allow_credentials）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 — 库存/基础数据
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(auth.router)
app.include_router(warehouses.router)
app.include_router(dashboard.router)
app.include_router(inventory.router)
app.include_router(inbound.router)
app.include_router(outbound.router)
app.include_router(waves.router)
app.include_router(returns.router)
app.include_router(transfers.router)
app.include_router(counts.router)
# 注册路由 — 业财一体（销售订单 / 财务 / 经营驾驶舱）
app.include_router(sales_orders.router)
app.include_router(finance.router)
app.include_router(executive.router)


@app.get("/")
def root():
    return {"message": "WMS API is running. Visit /docs for API documentation."}
