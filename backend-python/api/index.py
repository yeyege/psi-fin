"""Vercel Serverless 入口：把 FastAPI(ASGI) 应用用 Mangum 包装成 Vercel Python 函数。

- Vercel 以 `handler` 作为函数入口。
- lifespan="auto"：冷启动时执行一次 app.main 的 startup（建表 + 写种子数据），
  之后同一实例复用，避免每次请求都初始化。
- sys.path 追加 backend-python 根目录，使 `app` 包与 `init_data` 模块可被导入。
"""
import os
import sys

# backend-python 根目录（本文件位于 backend-python/api/index.py）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

handler = Mangum(app, lifespan="auto")
