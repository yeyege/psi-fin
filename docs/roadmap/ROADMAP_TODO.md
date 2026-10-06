# WMS / PSI-FIN 全局待办总览（ROADMAP / TODO）

> 本文档是项目级**总待办入口**，双轨并行：**A 轨 = 工程质量验收整改**（对照软件工程标准），**B 轨 = 核心业务功能 P0-P3**。
> 详细单点方案见对应 openspec change 或 NOTES.md。
> 主干与对外视图见同级 [`./README.md`](./README.md)（本文件为内部执行明细）。
> 维护约定：每完成一个阶段或 change 后同步更新本表；测试/文档数字以**仓库真实运行结果**为准。
> 最近一次全面代码审核：2026-09-22（后端 pytest **127** 例全绿、前端 vitest **31** 例全绿、Playwright E2E 4 spec）。

---

## 〇、审核结论速览（软件工程验收标准）

| 维度 | 评级 | 主要缺口 |
|---|---|---|
| 正确性 / 数据完整性 | 🟨 | 无 DB 迁移、金额用 float（违反自身 Decimal 标准） |
| 安全 | 🟨 | 登录无速率限制；其余（PBKDF2 加盐、参数化查询、token 可撤销）良好 |
| 可观测性 | 🟥 | 全项目零结构化日志 |
| 测试 | 🟩/🟨 | 覆盖良好；但 E2E 未进 CI、无 lint、无覆盖率门 |
| 架构 / 可维护性（后端） | 🟩 | 四层解耦 + 枚举/信封/Schema 收敛已落地 |
| 架构 / 可维护性（前端） | 🟨 | 超大组件、api 层手写无 codegen、双看板碎片 + 孤儿文件 |
| CI/CD / 部署 | 🟨 | 缺 lint/E2E 阶段、docker build 缺 buildx |
| 文档一致性 | 🟨 | VERIFICATION.md 严重过期（README 数字漂移与 openspec 可见性已于 2026-09-26 处理，见 Q13/Q14） |

---

## 一、A 轨 · 工程质量整改待办（按优先级）

> 原则：先「数据正确与可信」→「可观测与守门」→「前端可维护」→「文档/仓库一致」。
> 排序上 A 轨的 🟥 项应优先于 B 轨的 P1+ 功能扩张。

### A-P0 数据完整性与正确性（阻塞级）

| # | 项目 | 现状与证据 | 验收标准（DoD） |
|---|---|---|---|
| Q1 | **落地 Alembic 迁移** | 依赖含 `alembic` 但无 `alembic.ini` / `versions/`，schema 仅靠 [main.py](../../backend-python/app/main.py) lifespan 的 `create_all` | 初始化 alembic；生成 baseline 迁移；CI 增加 `alembic upgrade head` 冒烟；后续任何列变更走迁移脚本。**是 B 轨 #17（退货关联）前置** |
| Q2 | **金额 float → Decimal/Numeric(18,2)** | [models/finance.py](../../backend-python/app/models/finance.py) `total_amount/unit_price/amount=Float`；[finance_service.py](../../backend-python/app/services/finance_service.py) `round(float,2)`；accounting 同 | 模型列改 `Numeric(18,2)`、服务层用 `Decimal` 计算、序列化稳定两位小数；补金额累加/借贷平衡的精度单测；对齐记忆「财务金额精度规范」 |
| Q3 | ~~扣减/锁定循环加次数上限~~ **已处理（2026-10-04）** | 原 `deduct_stock`/`lock_stock`/`ship_stock` 的 `while remaining>0` + `rowcount==0: continue` 无 attempt cap | 已加 `MAX_STOCK_CONFLICT_RETRY = 50`（只统计冲突次数，故跨批次消耗多行的合法长循环不会被误伤）与共用放弃函数 `_conflict_give_up`（BusinessError 409）。取证：`tests/test_inventory_service.py::test_stock_mutation_gives_up_on_persistent_conflict[deduct_stock\|lock_stock\|ship_stock]`；测试侧另设 `_TEST_SPIN_CEILING=400` 护栏，未修前红态报“重试 401 次仍未收手”而非挂死 CI |

### A-P1 可观测性与 CI 守门（高价值）

| # | 项目 | 现状与证据 | 验收标准（DoD） |
|---|---|---|---|
| Q4 | **结构化日志 + 请求中间件** | 全后端仅 `print`（init_data）、无 `logging`；前端仅 console | 引入标准库 `logging`（JSON formatter），FastAPI 请求日志中间件带 request-id / 耗时 / 状态；错误路径统一记录 BusinessError |
| Q5 | **CI 补 lint 阶段** | [ci.yml](../../.github/workflows/ci.yml) 无 lint；后端无 ruff、前端无 eslint、[package.json](../../frontend-vue/package.json) 无 `lint` 脚本 | 后端加 `ruff check`（pyproject 配 `[tool.ruff]`）、前端加 eslint + `npm run lint`，均纳入 CI |
| Q6 | **CI 补 Playwright E2E 阶段** | 有 `e2e/*.spec.ts` 与 `npm run test:e2e`，但 CI 不跑 → 静默腐化 | CI 增 job：起后端+前端（或 Mock 模式）跑 e2e；产物上传 `playwright-report` |
| Q7 | **修复 docker-build job** | ci.yml 用 `docker/build-push-action@v5` 但未 `docker/setup-buildx-action` | 补 buildx 初始化；或改回 `docker build`；确认 CI 该 job 实际通过 |
| Q8 | **测试覆盖率门槛（选做）** | 无覆盖率报告/门 | `pytest-cov` + vitest coverage，设阈值并出报告 |

### A-P2 前端可维护性（结构性重构，风险低收益高）

| # | 项目 | 现状与证据 | 验收标准（DoD） |
|---|---|---|---|
| Q9 | **拆分超大单文件组件** | [DashboardView.vue](../../frontend-vue/src/views/DashboardView.vue) 1555 行、[LoginView.vue](../../frontend-vue/src/views/LoginView.vue) 1092 行，视图/图表配置/Mock 混杂 | 抽出子组件与 `composables`；Mock 数据移到 `src/api/mock` 或 fixture；单组件目标 < 400 行；行为/视觉不变 |
| Q10 | **收敛双看板 + 删孤儿** | 路由 [index.ts](../../frontend-vue/src/router/index.ts) 中 `/dashboard`(DashboardView 仓储看板) 与 `/bi`(BiWorkbenchView) 并存；`ExecutiveView.vue` 154 行已无引用（`/executive` 重定向到 `/bi`） | 明确两者定位（保留则去重、共用图表主题），**删除孤儿 `ExecutiveView.vue`**；[router/index.ts](../../frontend-vue/src/router/index.ts) 守卫 `JSON.parse` 加 try/catch |
| Q11 | **API 层去手写样板** | [api/index.ts](../../frontend-vue/src/api/index.ts) 718 行集中手写、类型与后端 camel 手工对齐 | 按域拆分子模块（`api/inventory.ts` 等）+ 统一 client；探索从 OpenAPI 生成 TS 类型（后端已有 `/docs` schema），消除契约漂移 |

### A-P2 文档与仓库一致性

| # | 项目 | 现状与证据 | 验收标准（DoD） |
|---|---|---|---|
| Q12 | **更新 VERIFICATION.md** | [VERIFICATION.md](../../VERIFICATION.md) 写「80 passed / wms.db / 旧测试清单」，实际 130 例、`psi_fin.db`（金额迁移后新增 3 条回归） | 重跑测试刷新分文件用例表、DB 文件名、环境；补上 PostgreSQL 迁移轨与 `scripts/check_money_columns.py` 取证口径；与 README 对齐 |
| Q13 | ~~README 数字对齐~~ **已处理（2026-09-26）** | [README.md](../../README.md) 原写「后端 126 / 合计 157+ / 4 个 E2E」；金额迁移后实测为后端 130、前端 31、E2E 12 | 已按实测值刷新，并补上 CI 的 PostgreSQL 迁移轨与 `migrations/` 目录说明。DoD：每个数字都来自一次真实运行，不再手抄 |
| Q14 | **openspec 资产可见性策略** → **已决策：入库** | 原 [.gitignore](../../.gitignore) 忽略 `openspec/` 与 `.claude`，但 `code-review` 的 Spec 轴必须以 `openspec/changes/<name>/` 为事实源，clean clone 上不能悬空 | 2026-09-26 提交 `08e034d`：`openspec/` 全量入库；`.claude` 改为逐层白名单（只放行 `commands/opsx/` 与 `skills/openspec-*/`，个人求职材料仍忽略）。**遗留**：`preview`、`assets` 两条无前导斜杠的全局匹配仍不改（会翻转大量文件的跟踪状态），单独开一轮 |
| Q15 | **清理死文件 wms.db** | [backend-python/wms.db](../../backend-python/wms.db) 上轮尝试删除被进程占用失败（已被 gitignore，仅本地） | 关闭占用进程后删除；确认无脚本引用（[database.py](../../backend-python/app/database.py) 仅用 psi_fin.db） |

---

## 二、B 轨 · 核心业务功能阶段进度（P0-P3）

排序原则：先「正确性与数据可信」→「作业效率与性能」→「系统能力与架构」→「集成与扩展」。

### P0 — 正确性与数据可信

| # | 项目 | 状态 | 关联资产 |
|---|---|---|---|
| 1 | 盘点闭环（4 种范围快照 / 实盘录入 / 自动盘盈盘亏 / 准确率） | ✅ 已完成 | NOTES.md §P0-1 |
| 2 | **严格批次 FIFO + 效期（FEFO、临期/过期/呆滞预警）** | **已开工（5/12）** | openspec change `p0-2-strict-fifo-expiry`：组 1（`batch_lifecycle` 纯函数 + 阈值常量）、组 2（`FEFO_ORDER_KEYS` 已接管三个扣减入口的候选排序，旧 `Inventory.id` 排序已不在代码里；3 条 FEFO 用例）与组 3（两个查询出口返回批次效期/库龄/状态，批次列表支持 `status` 筛选）已落。剩余：组 4 拣货/发货同序回归、组 5 前端预警展示、组 6 集成验证 |
| 3 | 复核扫码验货（逐件校验 SKU+批次+数量） | 待办（未设计） | 状态机已有 REVIEWED，缺扫码录入实现 |
| 4 | 实时对账任务（行锁代码已有，对账缺失） | 待办 | 依赖 Q4 可观测性；PG 迁移已完成（见 B 轨 #10），原「依赖 P2 迁移 PG」已不成立 |

### P1 — 作业效率与系统性能

| # | 项目 | 状态 |
|---|---|---|
| 5 | 波次策略引擎（类型/时效/承运商聚合 + S 形路径；现为 M5 基础波次） | 待办 |
| 6 | 上架与补货策略（利用率/周转率推荐 + 自动补货；现为库位优先级） | 待办 |
| 7 | 前端性能与看板升级 | 部分完成（趋势/环形/热力✅ / 虚拟滚动待办；见 Q9/Q10） |

### P2 — 系统能力与架构升级

| # | 项目 | 状态 | 依赖 |
|---|---|---|---|
| 8 | RBAC 细粒度权限（角色-权限-资源 + 审计日志；现为 admin/operator） | 待办 | 审计日志依赖 Q4 日志 |
| 9 | Redis 缓存 + MQ 削峰 | 待办 | — |
| 10 | 数据库升级 PostgreSQL（行锁/备份/监控） | **已完成（2026-10-07）** | compose 主库切 `postgres:16`（MySQL 8 收进 `--profile mysql`）、`tests/conftest.py` 与 CI `backend-test` 均跑在 PG 16 上，线上演示本就是 Neon PostgreSQL。原「前置 Q1 Alembic」已满足。**遗留**：D12 连接池参数（tasks 1.6b）、启动入口接 `alembic upgrade head`（tasks 1.5b）、`pg_dump` 备份运维文档（tasks 1.9） |

### P3 — 集成与扩展

| # | 项目 | 状态 |
|---|---|---|
| 11 | ERP/TMS/电商平台集成（网关 + Webhook + 幂等补偿） | 待办 |
| 12 | 多货主/多仓库/3PL 计费 | 待办 |
| 13 | PDA / 移动端 H5 | 待办 |
| 14 | 序列号与质检（QC） | 待办 |
| 15 | 运营报表与预警推送（邮件/企微） | 待办 |

### 业务体验补充（销售/退货盘点新增）

| # | 项目 | 优先级 | 状态 | 现状与改动点 |
|---|---|---|---|---|
| 16 | 销售订单列表补「商品明细」展示 | P2（纯前端小改） | 待办 | 后端已返回 `items`（productName/quantity/unitPrice/amount），仅 [SalesOrdersView.vue](../../frontend-vue/src/views/SalesOrdersView.vue) 未渲染明细；无后端/迁移 |
| 17 | 退货关联销售订单 | P1（跨前后端 + 财务口径待定） | 待办 | [ReturnOrder](../../backend-python/app/models/orders.py) 无指向 sales_orders 的外键；需模型加 `source_order_no`（**迁移依赖 A 轨 Q1**）+ payload 带来源 + 前端带出历史订单。**口径待定**：是否强制关联已发货订单、退货是否红冲应收 |

---

## 三、openspec change 资产状态

> `openspec/` 已于 2026-09-26 随 `08e034d` 入库（Q14 的决策），不再是本地专有资产。
> 本表与 `openspec list --json` 同源，最近刷新 2026-10-04；完成数以该命令实测为准，不手抄。

### 在飞（2）

| change | 范围 | 进度 | 状态 |
|---|---|---|---|
| `oss-finance-ai-platform` | 开源门面 + 财务内核 + AI 层（Phase 0–4） | 10/40 | Phase 0 新增落地：tasks 1.6a（compose 主库切 PG 16）与 1.7b（全量单测跑在 PG 16、本地与 CI 同步）；1.9 的「既有审计口径」已订正为不存在并拆出 1.9a。Phase 1 仍仅 2.0 + 2.1 落地（`models/accounting.py` + `services/accounting_service.py` + 单测；2.0d 分录缺科目已改 `BusinessError`）。**会计内核尚无 router**（`routers/` 无 `accounting.py`、`main.py` 未挂载）→ 2.2 未开始；Phase 3 的 `app/ai/` 目录不存在。分母从 35 变 40 是因为本轮新增了子项，不是任务被拆细。冲突项见下表 |
| `p0-2-strict-fifo-expiry` | 严格 FIFO + 效期 | 5/12 | **推进中**。组 1（`batch_lifecycle` 纯函数）、组 2（`FEFO_ORDER_KEYS` 三入口共用 + 3 条 FEFO 用例）与组 3（location 视图与批次列表返回效期/库龄/状态字段，`GET /api/inventory/batches` 支持 `status` 筛选）完成，全量 152 passed。剩余 7 项未实施，**下一组是组 4**（tasks 4.1：「拣货与发货同序」的回归断言 —— 目前同序仅由三入口共用排序隐式保证，无测试锁住，任一入口未来私改排序不会红灯）。⚠ 组 2 带走一个跨库坑：`with_for_update()` 必须改 `of=Inventory`，否则 PG 下「排序键取自批次表 → outerjoin Batch」会撞上「FOR UPDATE cannot be applied to the nullable side of an outer join」；MySQL 方言将 `of` 丢弃、渲染裸 `FOR UPDATE`（锁范围偏大，不破不变量）。细节见该 change `tasks.md` 各组完成记录 |

### 已归档

| change | 进度 | 归档处置 |
|---|---|---|
| `bi-workbench-vue-integration` | 19/19 | `archive/2026-10-04-…`；delta 已合入 `specs/bi-workbench/{shell,overview,inventory-analysis,flow-analysis,efficiency,mock-data}`，共 34 条 Requirement |
| `deploy-pages-mock-demo` | 14/14 | `archive/2026-10-04-…`；已合入 `specs/deployment/{mock-api,pages-static-site}` |
| `bi-dashboard-apple-style` | 23/23 | `archive/2026-10-04-…`，**走 `--skip-specs`**：交付物是 `preview/apple-store-wms.html` 静态原型，同一能力已由 `bi-workbench-vue-integration` 移植进 Vue，不合 `specs/bi-dashboard/`，免生两版现状规格 |
| `business-console-demo` | 6/8 | 2026-09-12 已归档；本表此前仍列为 in-progress，已订正 |

### 待裁定（`code-review` Spec 轴冲突项）

| # | 冲突 | 两侧证据 | 需定的口径 |
|---|---|---|---|
| C1 | 凭证号 —— **已裁定（2026-10-04）：改 D14，代码不动** | `design.md` D14 已划线保留原决策并附三条取代理由（`period_code` 已满足聚合 / 不可变账簿改标识符代价最高 / 本项目声明非报账报税用途）；`tasks.md` 2.0 与 2.0c 已收口 | 无需再定。旧版本行写的「两侧都主张权威」已不成立 |
| C2 | 主库 —— **已消解（2026-10-07）** | `docker-compose.yml` 已改 `postgres:16` 为主库、MySQL 进 `--profile mysql`，D17 的现在时不再超前于现实（见 tasks 1.6a）。驱动口径也已收口：D17「迁移成本」段与本表下方原写「切 `psycopg[binary]`」均已划线，由 1.6c / D17 驱动口径修正条取代（实装 `psycopg2-binary`） | 无需再定；评审按修正条而非原句判定 |
| C3 | D10 已订正文本 | `design.md` L95「业务域暂不改动」已被 L97 的 2026-09-26 修正取代，但**原文未删且排在前面** | 把被否决的原文划掉而非就地注释，否则评审仍会命中旧半句 |

---

## 四、下一步行动（建议顺序）

1. **A 轨 Q1（Alembic）+ Q2（Decimal）**：数据完整性阻塞项，且 Q1 同时解锁 B 轨 #10（PG）与 #17（退货关联）。⚠ 本表 §一 Q1/Q2 行的现状描述已过期——`alembic.ini`、`migrations/versions/`（`0001_baseline`、`0002_money_numeric`）、`app/common/money.py` 均已存在（见 D10/D11 进度注），Q1 实际只剩 1.5b/1.5c（启动入口与 CI 漂移门），**待单独核实后刷新 §一**。
2. **A 轨 Q4（日志）+ Q5/Q6/Q7（CI 守门）**：建立可观测性与「不腐化」的流水线护栏。
3. **A 轨 Q12/Q13（文档）**：低工作量，先止住 VERIFICATION/README 漂移。
4. ~~**裁定 §三 C1–C3**~~ **C1 已裁定（2026-10-04，改 D14 不动代码）、C2 已随切库消解（2026-10-07）**；只剩 C3（D10 旧文本未删）。不定就一直是评审误判源——`code-review` 已加 2a freshness gate，会把它们降级成 `## Conflict` 而非错判，但降级不等于解决。
5. **B 轨 P0-2**：**已决定开工（2026-10-04）**，按 `tasks.md` 分组推进。组 1、组 2、组 3 完成（2026-10-07）。**下一组是组 4**（tasks 4.1：「拣货与发货同序」回归断言）—— 它是组 2 那改排序的唯一定锁手段，不要再当「已由共享实现保证」略过；其后是组 5（前端预警展示）与组 6（集成验证）。
6. **A 轨 Q9/Q10/Q11（前端重构）**：与功能扩张并行推进，纯前端、风险低。Q10 的孤儿 `ExecutiveView.vue`（`/executive` 已重定向）随本轮归档确认仍未删，归 Q10 处理。
7. ~~收尾 `business-console-demo`、归档 `bi-dashboard-apple-style`~~ **已完成（2026-10-04）**：三个 complete change 已归档，在飞池 5 → 2，`openspec validate --all` 15 项全绿。

---

## 相关文档

- [NOTES.md](../../NOTES.md)：开发说明、AI 沉淀、遇到的问题与 P0-P3 详述
- [MVP_DESIGN.md](../../MVP_DESIGN.md)：M1-M7 里程碑历史设计
- [TASKS.md](../../TASKS.md)：任务与进展实录（以仓库真实代码为准）
- [VERIFICATION.md](../../VERIFICATION.md)：交付验证记录（**待按 Q12 更新**）
- [docs/API_SPEC.md](../API_SPEC.md) / [docs/PRD.md](../PRD.md)
- [`openspec/changes/*/tasks.md`](../../openspec/changes/)：各 change 实施待办（`code-review` Spec 轴事实源，随仓库分发；**须经该 skill 的 2a freshness gate 校验后才可用**，backlog change 不得充当事实源）
