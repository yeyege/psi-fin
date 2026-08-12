# ===== WMS 后端（FastAPI）=====
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖 + 业务代码（pip install . 需 app 包存在，先整体拷贝）
# 国内网络使用清华 PyPI 镜像（容器内网络不走 Docker daemon 代理）；加大超时/重试防断流
COPY . .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple .

EXPOSE 8000

# 启动：lifespan 自动建表 + 写入种子数据
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
