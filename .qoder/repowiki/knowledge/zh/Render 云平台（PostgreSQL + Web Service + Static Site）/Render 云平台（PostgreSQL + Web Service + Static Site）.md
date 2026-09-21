---
kind: external_dependency
name: Render 云平台（PostgreSQL + Web Service + Static Site）
slug: render
category: external_dependency
category_hints:
    - vendor_identity
    - client_constraint
scope:
    - '**'
source_files:
    - render.yaml
    - README.md
---

### 角色与集成点
- 生产部署目标：`render.yaml` Blueprint 定义三个资源——PostgreSQL 16（`psi-fin-db`）、Python Web Service（`backend-python/`，`uvicorn app.main:app`）、静态站点（`frontend-vue/dist`）。
- 数据库连接串由 Render 通过 `fromDatabase` 自动注入环境变量 `DATABASE_URL`，格式为 `postgresql://...`，SQLAlchemy 2.0 可直接识别。
- 前端构建产物通过 `VITE_API_BASE` 指向后端域名（模板中为 `https://REPLACE_WITH_BACKEND_URL.onrender.com/api`），需手动替换。

### 关键约束
- 免费层限制：PostgreSQL 免费版 30 天后回收；Web Service 空闲 15 分钟休眠，首次访问冷启动约 30~60s。
- 本地开发默认用 SQLite（`psi_fin.db`、`wms.db`），生产切换 PostgreSQL 仅靠 `DATABASE_URL` 环境变量，无需改代码。
- 另有 Vercel 在线演示（`psi-fin.vercel.app` / `wms-silk.vercel.app`），但当前 Blueprint 以 Render 为主。