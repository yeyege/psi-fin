---
kind: external_dependency
name: Neon Serverless PostgreSQL（在线演示数据库）
slug: neon
category: external_dependency
category_hints:
    - vendor_identity
    - client_constraint
scope:
    - '**'
source_files:
    - README.md
---

### 角色与集成点
- README 明确说明在线演示后端使用 **Vercel Serverless + Neon PostgreSQL**，即生产演示环境的数据库托管在 Neon。
- 项目通过 `DATABASE_URL` 环境变量接入，不关心底层是本地 SQLite、MySQL 容器还是 Neon PostgreSQL。

### 关键约束
- 仅用于在线演示（`wms-silk.vercel.app`），非本地开发默认库。
- 连接方式遵循 SQLAlchemy 标准 URL，无特殊 SDK。