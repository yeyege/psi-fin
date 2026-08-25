# ===== WMS 后端（FastAPI）=====
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖 + 业务代码（pip install . 需 app 包存在，先整体拷贝）
# 国内网络：优先清华源，失败自动 fallback 到腾讯云/阿里源；加大超时/重试
COPY . .
RUN pip install --no-cache-dir --timeout 180 --retries 15 \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --extra-index-url https://mirrors.cloud.tencent.com/pypi/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn \
        --trusted-host mirrors.cloud.tencent.com \
        . \
    || pip install --no-cache-dir --timeout 180 --retries 15 \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com \
        .

EXPOSE 8000

# 启动：lifespan 自动建表 + 写入种子数据
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
