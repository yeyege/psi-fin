# WMS MVP 设计 · 开发路线 · 进度追踪

> 本文档为 **活文档**：设计确定后按此执行，每完成一个里程碑同步更新「开发进度」。
> 定位：在现有测试题交付（必做+选做全绿）基础上，对标领星 WMS 补齐业务闭环的增量规划。

---

## 一、项目现状盘点（2026-08-12）

**技术栈**：Python/FastAPI + SQLAlchemy + SQLite（已选）+ Vue3/Element Plus + Pinia + Vite

**已完成**：

| 域 | 能力 | 状态 |
|---|---|---|
| 基础数据 | 商品（SKU/尺寸重量）、仓库→库区→库位（优先级） | ✅ 已交付 |
| 入库 | 手动创建（`IN-YYYYMMDD-XXX`）、收货上架、批次生成、事务+流水、状态机 `PENDING→COMPLETED` | ✅ |
| 库存 | `(product, location, batch)` 三维 + 可用/锁定分离、全量流水、服务端分页+索引、低库存高亮 | ✅ |
| 出库 | 手工出库、拣货锁定防超卖、复核验货、发货扣减、状态机 `PENDING→PICKED→REVIEWED→SHIPPED`、整单回滚 | ✅ |
| 库内作业 | 移库、库存调整（盘盈/盘亏）、批次、流水 | ✅ |
| M1-M7 扩展 | 客户管理、商品 FNSKU/箱规、数据看板、退货管理（RETURN_IN 流水）、波次拣货、复核验货、用户权限（User/Role+登录+鉴权） | ✅ |
| 工程化 | Docker Compose、Playwright E2E（inbound/returns/wave 3 条）、GitHub Actions CI | ✅ |
| 测试 | pytest 72 例 + vitest 14 例 | ✅ |

**API 面**：基础 27 个接口 + M1-M7 新增（客户/看板/退货/波次/复核/鉴权/用户管理）合计 40+ 个接口

---

## 二、MVP 目标与范围

### 目标
跑通一条**完整的业务纵链**：`客户 → 商品(含FNSKU/箱规) → 入库/退货收货 → 库存(四维+流水) → 波次拣货 → 复核验货 → 发货扣减 → 数据看板`，并补上用户权限。

### 范围划分

**P0 — 本轮落地（补齐核心闭环）**
| 模块 | 内容 | 前后端 |
|---|---|---|
| M1 客户管理 | Customer 表（分层 A/B/C），商品/出库单/退货单归属客户 | 是 |
| M2 商品字段扩展 | 新增 FNSKU、每箱数量 caseQty | 是 |
| M3 数据看板 | 今日出入库单数、库存总量、低库存预警、待处理单据 | 是 |
| M4 退货管理 | 退货单（FBA/买家/服务商）→ 收货登记 → 换标/转正品/报废 | 是 |
| M5 波次拣货 | 出库单聚合生成波次 → 拣货单，按库位优先级推荐库位 | 是 |
| M6 复核验货 | 拣货完成后复核数量 → 确认发货 | 是 |
| M7 用户权限 | User/Role（admin/操作员）+ 登录接口 + 简单鉴权 | 是 |

**P1 — 增强（本期不实现，设计预留）**
- 计费：计费规则（入库/操作/仓储/出库费）+ 报价方案 + 账单明细 + 币种/汇率
- 库存：箱级库存（case 维度）、退货库存视图、Excel 初始化导入
- 报表：出入库效率看板、库容分析
- 物流：物流商配置（mock FedEx/UPS）、面单占位、轨迹同步 mock
- 时效预警：入库/出库超时高亮

**P2 — 架构预留（仅设计）**
- 集成适配器：`erp_adapter` / `carrier_adapter` 接口（Amazon/Shopify/领星ERP 对接位）
- PDA 移动端（复用同一 API 集）
- AI 打包（最小体积计算）
- 多语言/时区、多仓实例化

---

## 三、架构设计

### 3.1 分层（沿用现有代码约定）

```
routers(接口) → services(业务/事务/状态机) → models(ORM) → SQLite
                └── inventory_service 统一库存入口（add/deduct/lock/ship + 强制流水）
```

### 3.2 数据模型演进

```
现有：Product ── Inventory(product, location, batch, avail/locked) ── InventoryFlow
新增：
  Customer ─┬─ Product(+fns_ku, case_qty)      Wave ─┬─ PickingOrder ── PickingItem(含推荐库位)
  ReturnOrder ─ ReturnItem ─(收货: 转正品→inventory / 报废)        └─ OutboundOrder
  User ─ Role
```

### 3.3 状态机设计

| 单据 | 状态机 |
|---|---|
| 退货单 | `PENDING(待收货) → RECEIVED(已收货登记) → DONE(处理完成: 换标/转正品/报废)` |
| 波次 | `CREATED(已生成) → PICKING(拣货中) → COMPLETED(已完成)` |
| 出库单 | 扩展：`PENDING → PICKED → REVIEWED(已复核) → SHIPPED` |
| 拣货单 | `CREATED → PICKING → PICKED(锁定完成)`，与出库单 PICKED 联动 |

### 3.4 API 设计预留

| 模块 | 接口 |
|---|---|
| 客户 | `GET/POST /api/customers`，`GET /api/customers/{id}` |
| 商品 | `ProductPayload` 增加 `fnsKu`、`caseQty` |
| 退货 | `POST /api/returns`，`POST /api/returns/{id}/receive`，`POST /api/returns/{id}/finish` |
| 波次 | `POST /api/waves`（按条件聚合出库单），`GET /api/waves`，`GET /api/picking-orders` |
| 复核 | `POST /api/outbound-orders/{id}/review` |
| 看板 | `GET /api/dashboard/summary` |
| 权限 | `POST /api/auth/login`，`GET /api/users`，`POST /api/users` |

### 3.5 前端页面地图（9 → 13 页）

```
数据看板 Dashboard(M3) ★新增
├─ 业务：入库 / 出库(复核按钮) / 波次拣货(M5)★ / 退货(M4)★ / 移库 / 调整
├─ 库存：库存 / 批次 / 流水
├─ 基础：商品(FNSKU/箱规) / 客户(M1)★ / 仓库库位
└─ 设置：用户权限(M7)★
```

### 3.6 开发规范（执行时强制遵守）

1. **契约**：Schema 用 `CamelModel`（`alias_generator=to_camel`），前后端 camelCase。
2. **单号**：`generate_order_no(db, Model, prefix)`，前缀 `RT`(退货) / `WV`(波次) / `PK`(拣货)。
3. **库存**：一切库存变动走 `inventory_service` 统一入口，自动写流水。
4. **事务**：多表写操作单事务，失败整单回滚；库存不足先校验后操作（防超卖）。
5. **性能**：列表查询 joinedload 防 N+1，筛选列建索引，服务端分页。
6. **测试**：每模块后端 `pytest` ≥ 2 用例（状态机 + 异常分支）；前端关键纯函数 vitest。
7. **提交**：小步提交，`feat(backend): 退货单状态机` 风格，一个模块一个 commit。

---

## 四、开发路线图（执行顺序）

按依赖排序，每个里程碑独立可验证（后端测试绿 + 前端页面可用）：

| 顺序 | 里程碑 | 内容 | 验收 |
|---|---|---|---|
| ① | M1+M2 基础数据 | 客户管理（后端+前端）、商品 FNSKU/箱规 | 客户 CRUD、商品表单新字段 |
| ② | M3 数据看板 | 聚合 API + Dashboard 页 | 统计卡片正确 |
| ③ | M4 退货管理 | 退货单状态机（收货转正品/报废）+ 页面 | 退货→收货→库存增加链路通 |
| ④ | M5 波次拣货 | 波次聚合 + 拣货单 + 推荐库位 + 页面 | 多出库单生成波次→拣货锁定 |
| ⑤ | M6 复核验货 | 出库单 REVIEWED 状态 + 复核接口 + 页面按钮 | 复核后发货 |
| ⑥ | M7 用户权限 | User/Role + 登录 + 鉴权 | 未登录 401、角色隔离 |

> 工期提示：①-⑥ 按序推进，每步跑通后同步更新本文档「开发进度」并提交。

---

## 五、开发进度追踪

> ✅ 完成 ｜ 🚧 进行中 ｜ ⬜ 未开始

| 里程碑 | 后端 | 前端 | 测试 | 状态 |
|---|---|---|---|---|
| M1 客户管理 | ✅ | ✅ | ✅ | ✅ |
| M2 商品 FNSKU/箱规 | ✅ | ✅ | ✅ | ✅ |
| M3 数据看板 | ✅ | ✅ | ✅ | ✅ |
| M4 退货管理 | ✅ | ✅ | ✅ | ✅ |
| M5 波次拣货 | ✅ | ✅ | ✅ | ✅ |
| M6 复核验货 | ✅ | ✅ | ✅ | ✅ |
| M7 用户权限 | ✅ | ✅ | ✅ | ✅ |

---

## 六、提交前检查清单（交付前必读）

> 这些是拉开「作业」与「工程交付物」差距的关键项。已按优先级分类：
> 🔴 必须达标（否则可能被拒）｜🟠 强烈推荐（加分项）｜🟡 锦上添花（量力而行）。

### 🔴 第一优先级：硬性指标（必须 100% 完成）

1. **全量测试通过（最关键）**
   - 后端：`uv run pytest` → **72 例全绿**（不能有 F 或 s）
   - 前端：`npx vitest run` → **14 例全绿**
   - 注意：跑测试前确保 8000 端口未被占用；pytest 使用独立临时库（不依赖 wms.db），但 `wms.db` 需可由 lifespan 自动建表
2. **NOTES.md 必须完整（评审最看重）**
   - 用了哪些 AI 工具、如何组织提示词（子代理分工/角色设定）
   - 1-2 个典型 Bug 及解决（如「库存并发扣减防超卖」：SUM 校验 + 条件 UPDATE + 回滚）
   - 如果多两天会优化什么（权限管理增强、消息队列/异步作业）
3. **Git 提交历史干净且有意义**
   - 小步提交：`feat(backend): …` / `fix: …` / `test: …` 风格，一个模块一个 commit
   - 严禁只有一个「finish all」大提交（当前 15 个小 commit 已满足）

### 🟠 第二优先级：强烈推荐（加分项，做「最小可用集」）

| 项 | 目标 | 当前状态 |
|---|---|---|
| Docker 一键启动 | 根目录 `docker-compose.yml`（后端+前端+MySQL），`docker-compose up -d` 后浏览器可访问前端 | ✅ **已验证**：`docker compose up -d --build` 全绿（mysql healthy + backend/frontend 运行，登录接口返回 token，前端 HTTP 200） |
| Playwright E2E 冒烟 | 核心链路「创建入库单→成功提示」等，`npx playwright test` 绿条 | ✅ 已有 inbound / returns / wave 3 条，3/3 通过 |
| CI/CD（GitHub Actions） | push 触发，仅执行 `pytest` + 前端 `build`/`vitest`，不推镜像 | ✅ 已有 `.github/workflows/ci.yml` |

### 🟡 第三优先级：锦上添花（时间不够可提一句）

- 关键复杂逻辑简短注释（库存加减 / 防超卖已注释）
- 1920×1080 下美观即可，无需移动端适配
- 性能：服务端分页已做，测试数据量小无需虚拟列表

### 📩 发送前「最终自检清单」（逐项打钩）

1. **「新鲜克隆」测试（最重要）**
   - 将当前项目目录移走 → 在另一目录 `git clone <仓库地址>`（或解压 ZIP）
   - 严格按 README 快速启动：`cd backend-python && uv sync && uv run uvicorn app.main:app`；`cd frontend-vue && npm install && npm run dev`
   - 一旦卡住立即修复，否则评审第一步就跑不起来
2. **检查无用大文件**：根目录无 `.venv` / `node_modules` / `__pycache__` / `.pytest_cache`（仓库提交时 .gitignore 已忽略；ZIP 打包必须删除）
3. **邮件正文与收件人**：
   - 主送 `zhangjiahui@gzyouliu.cn`，抄送 `jiangziqi@gzyouliu.cn`、`dengsuiming@gzyouliu.cn`
   - 标题建议「【WMS测试】你的姓名 - 全栈开发 - 已完成」
   - 附 GitHub 公开仓库地址（省权限麻烦）；若私有则添加对方为 Collaborator 或附 ZIP 链接
