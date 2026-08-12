# ===== WMS 后端（FastAPI）=====
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖 + 业务代码（pip install . 需 app 包存在，先整体拷贝）
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

# 启动：lifespan 自动建表 + 写入种子数据
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
