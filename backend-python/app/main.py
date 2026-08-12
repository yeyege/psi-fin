from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import products, warehouses, inbound, outbound, inventory, transfers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 初始化示例数据（仅当库为空时）。"""
    Base.metadata.create_all(bind=engine)
    from init_data import init_data
    init_data()
    yield


app = FastAPI(
    title="WMS API",
    description="仓储管理系统 API（对标领星WMS：批次库存 / 可用+锁定 / 全量流水 / 单据状态机）",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)
app.include_router(inbound.router)
app.include_router(outbound.router)
app.include_router(transfers.router)


@app.get("/")
def root():
    return {"message": "WMS API is running. Visit /docs for API documentation."}
