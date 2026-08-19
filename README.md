# WMS 仓储管理系统

一个对标领星 WMS 的简化版仓库管理系统，覆盖入库 / 出库 / 库存 / 波次拣货 / 退货 / 移库调拨 / 数据看板 / 用户权限等核心场景。后端 Python + FastAPI，前端 Vue 3 + Element Plus，支持 Docker 一键启动。

- 后端测试：**80 用例**（pytest，全部通过）
- 前端测试：**14 用例**（vitest，全部通过）
- E2E：Playwright 覆盖入库核心正向流程
- CI：GitHub Actions（pytest + 前端 build/vitest + docker build 校验）

---

## 核心特性

### 仓储模型
- **仓库 → 库区 → 库位** 三层结构，库位带优先级（上架推荐排序）
- **批次管理**：每次入库收货每个明细行生成独立批次，支持生产日期 / 有效期
- **库存分离**：`available_qty`（可用量）+ `locked_qty`（锁定量），隔离「已承诺未出库」库存
- **全量流水**：所有库存变动必须经 `inventory_service` 统一入口，强制写入 `inventory_flow`，记录变动前/后数量

### 业务单据（状态机驱动）
- **入库单**：`PENDING(待收货) → COMPLETED(已收货上架)`，创建不触碰库存，收货时生成批次 + 累加库存 + 写流水
- **出库单**：`PENDING → PICKED(已拣货锁定) → REVIEWED(已复核) → SHIPPED(已发货扣减)`，复核是发货前置环节
- **波次拣货**：出库单聚合生成波次，拣货单按库位优先级排序，拣货时锁定库存
- **退货单**：`PENDING → RECEIVED → DONE`，按处置方式（转正品 / 换标 / 报废）决定是否回补库存
- **移库 / 调整单**：直接完成并写双向流水

### 并发安全（防超卖）
- 行级 `SELECT ... FOR UPDATE`（SQLite 忽略、PostgreSQL 生效）
- 条件 UPDATE（`WHERE available_qty >= take`）+ 失败重读重试
- 先 `SUM` 校验总量，不足直接返回 False 无副作用
- 整单事务：任一明细失败 → 整单 rollback，不留半成品

---

## 技术栈

| 模块   | 技术选型                                            |
|--------|-----------------------------------------------------|
| 后端   | Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic v2 |
| 前端   | Vue 3 + TypeScript + Element Plus + Pinia + Vite    |
| 数据库 | SQLite（开发零配置）/ MySQL 8.0（容器）             |
| 测试   | pytest + vitest + Playwright                        |
| 部署   | Docker Compose（mysql + backend + frontend/nginx）  |
| CI     | GitHub Actions                                     |

> 前后端通过 `CamelModel` 统一 camelCase 契约，输入输出同时兼容。

---

## 项目结构

```
wms-test/
├── backend-python/           # FastAPI 后端
│   ├── app/
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── routers/           # API 路由（11 个模块）
│   │   ├── schemas/          # Pydantic 契约
│   │   ├── services/         # 业务服务（库存变动统一入口）
│   │   ├── common/           # 全局异常 / 通用响应
│   │   └── main.py           # FastAPI 入口（lifespan 自动建表 + 种子数据）
│   ├── tests/                # pytest 测试（80 用例）
│   ├── init_data.py          # 示例数据初始化
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend-vue/             # Vue 3 前端
│   ├── src/
│   │   ├── api/              # axios 客户端
│   │   ├── components/       # 通用组件（SummaryCards）
│   │   ├── router/           # 路由 + 登录守卫
│   │   ├── stores/           # Pinia 用户态
│   │   ├── utils/            # 纯函数（含单测）
│   │   └── views/            # 14 个业务页面
│   ├── e2e/                  # Playwright E2E
│   ├── Dockerfile
│   └── nginx.conf            # /api 反代到后端
├── docs/
│   └── API_SPEC.md           # API 接口规范
├── .github/workflows/ci.yml  # GitHub Actions CI
├── docker-compose.yml         # 一键启动全栈
├── NOTES.md                  # 开发说明（AI 使用 / Bug / 方案 / 测试）
├── MVP_DESIGN.md             # MVP 设计路线图
└── README.md
```

> Java（Spring Boot） / React 模板为初始测试题提供，本实现选用 **Python + FastAPI** 与 **Vue 3 + Element Plus**。

---

## 快速启动

### 方式一：Docker Compose（推荐，一键全栈）

```bash
# 可选：复制环境变量（不复制则使用默认值）
cp .env.example .env

# 一键构建并启动（mysql + backend + frontend）
docker compose up -d --build
```

- 前端：http://localhost:8080
- 后端 API 文档：http://localhost:8000/docs
- 默认账号：`admin / admin123`

### 方式二：本地开发（前后端分离）

**后端（FastAPI）**

```bash
cd backend-python
uv sync                                     # 安装依赖
uv run uvicorn app.main:app --port 8000     # 启动 http://localhost:8000（自动建表 + 种子数据）
uv run pytest                               # 运行测试（80 用例）
```

> 使用 SQLite，零配置；如需切换 MySQL，设置 `DATABASE_URL=mysql+pymysql://wms:wms@localhost:3306/wms?charset=utf8mb4`。

**前端（Vue 3）**

```bash
cd frontend-vue
npm install
npm run dev         # 启动 http://localhost:5173（/api 代理到 8000）
npm test            # 单元测试（14 用例）
npm run test:e2e    # Playwright E2E（自动拉起前后端）
```

### 方式三：根目录一键并发启动

```bash
npm install
npm start           # concurrently 同时拉起后端 + 前端
```

---

## 功能模块

### 必做任务
- **入库单创建**：单号 `IN-YYYYMMDD-XXX` 自动生成、多行明细、商品/库位级联选择、收货时事务内生成批次 + 累加库存 + 写流水
- **库存查询**：按商品汇总 / 按库位明细双视图、模糊搜索 + 仓库筛选 + 批次筛选、服务端分页、低库存（<10）整行红色高亮
- **Bug 修复**：① 商品删除前校验关联库存（软删除）② 商品列表编辑后保留当前页码

### 选做任务
- **出库单 + 防超卖**：锁定机制 + 原子扣减 + 整单回滚（含并发双线程防超卖测试）
- **单元测试**：后端 80 + 前端 14 用例
- **前端性能优化**：服务端分页 + 搜索防抖（300ms）+ 筛选逻辑抽离纯函数

### MVP 扩展（M1-M7）
- **M1 客户管理**：A/B/C 分层、CRUD + 软删除
- **M2 商品扩展**：FNSKU + 箱规（case_qty）
- **M3 数据看板**：今日单量 / 库存总量 / 低库存 / 在售商品 / 合作客户 8 张统计卡片
- **M4 退货管理**：FBA / 买家 / 服务商退件，转正品 / 换标 / 报废三种处置
- **M5 波次拣货**：波次聚合 + 拣货单按库位优先级排序 + 锁定库存
- **M6 复核验货**：发货前强制复核（`PICKED → REVIEWED → SHIPPED`）
- **M7 用户权限**：admin / operator 双角色、PBKDF2-SHA256 密码哈希、Token 鉴权、路由守卫

---

## API 概览

启动后访问 http://localhost:8000/docs 查看自动生成的 OpenAPI 文档，主要路由模块：

| 模块       | 路由前缀              | 说明                          |
|------------|-----------------------|-------------------------------|
| 认证       | `/api/auth`           | 登录 / 登出 / me              |
| 商品       | `/api/products`       | CRUD + FNSKU                 |
| 客户       | `/api/customers`      | CRUD + 软删除                 |
| 仓库       | `/api/warehouses`     | 仓库 / 库区 / 库位            |
| 库存       | `/api/inventory`      | 商品汇总 / 库位明细           |
| 入库       | `/api/inbound-orders` | 创建 / 收货                   |
| 出库       | `/api/outbound-orders`| 创建 / 拣货 / 复核 / 发货     |
| 波次       | `/api/waves`          | 生成 / 拣货                   |
| 退货       | `/api/return-orders`  | 创建 / 收货                   |
| 移库       | `/api/transfers`      | 移库单                        |
| 调整       | `/api/adjustments`    | 盘盈 / 盘亏                   |
| 看板       | `/api/dashboard`      | 聚合统计                      |
| 用户       | `/api/users`          | CRUD（仅 admin）              |

完整接口规范见 [docs/API_SPEC.md](./docs/API_SPEC.md)。

---

## 测试

```bash
# 后端单元测试（80 用例，不连真实数据库）
cd backend-python && uv run pytest

# 前端单元测试（14 用例）
cd frontend-vue && npm test

# 前端 E2E（Playwright，自动拉起前后端）
cd frontend-vue && npm run test:e2e
```

测试覆盖：入库累加 / 跨批次 FIFO 扣减 / 库存不足无副作用 / 锁定+发货 / 拣货防超卖（并发双线程）/ 移库双向流水 / 盘盈盘亏 / 退货回补 / 波次生成 / camelCase 契约 / 登录鉴权 等。

---

## CI / CD

[.github/workflows/ci.yml](./.github/workflows/ci.yml) 在 push / PR 到 master 时触发：

1. **后端 pytest**（不连真实数据库）
2. **前端** `npm run build`（类型检查 + 构建）+ `vitest`
3. **Docker 镜像构建校验**（前后端镜像可构建，不推送仓库）

---

## 默认账号与示例数据

启动时 `lifespan` 自动建表并写入种子数据（仅当库为空时）：

- **管理员**：`admin / admin123`
- **仓库**：广州主仓（WH-A）、深圳保税仓（WH-B）
- **库区**：正品区 / 残次品区
- **库位**：A-01-01 / A-01-02 / A-02-01 / A-D-01 / B-01-01 / B-01-02（带优先级）
- **商品**：5 个 SKU（含 FNSKU 与箱规）
- **客户**：3 家（A/B/C 分层）

---

## 文档

- [NOTES.md](./NOTES.md) — 开发说明（AI 使用 / Bug 修复 / 方案选型 / 测试覆盖）
- [MVP_DESIGN.md](./MVP_DESIGN.md) — MVP 设计路线图
- [docs/API_SPEC.md](./docs/API_SPEC.md) — API 接口规范
- [TASKS.md](./TASKS.md) — 任务清单

---

## License

本项目为全栈工程师测试交付物，仅供学习与评估用途。
