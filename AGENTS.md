# AGENTS.md

进销存 · 业财一体中后台（FastAPI + Vue 3）的开发约束。本文件固化所有 AI 工具与新同事
**必须遵守的硬规则**；细节背景见 `.qoder/repowiki/`、`docs/PRD.md`、`docs/API_SPEC.md`、`NOTES.md`。

## 1. 四层架构铁律（routers → services → models/schemas）

- **routers 只做薄 HTTP 层**：参数绑定、鉴权依赖、调用 service、包装响应，
  **禁止在路由函数里直接操作数据库或写业务规则**。
- **业务逻辑全部下沉 services**：状态机、校验、事务边界都在 service 内完成。
- **models 用 SQLAlchemy 异步声明式映射**；schemas 基于 `CamelModel`（Pydantic v2）定义请求/响应。
- **模块间只经 service 层调用**，禁止跨模块直接改他人表；新增路由须在 `app/main.py`
  用 `app.include_router` 显式挂载才对外暴露。
- 业务异常一律 `raise BusinessError(...)`（`app.common.errors`），由 `main.py` 全局异常处理器统一转 JSON。

## 2. 库存核心不变量（不可违反）

- **所有库存变动必须走 `inventory_service` 唯一入口**（`add_stock` / `deduct_stock`），
  **禁止直接 UPDATE 库存表**。
- **每一次库存变动强制写入 `inventory_flows` 流水**（表名复数，`models/inventory.py`），并以
  `FLOW_TYPE_*` / `ORDER_TYPE_*` 常量标注类型。
- 防超卖：行级 `SELECT ... FOR UPDATE` + 条件 UPDATE（`WHERE available_qty >= take`）+ 失败重读重试；
  任一明细失败 → **整单 rollback**，不留半成品。
- 单号统一用 `generate_order_no(db, Model, prefix)` 生成（IN/RT/ADJ 等前缀），IntegrityError 最多 5 次重试。

## 3. 统一响应与鉴权

- 所有接口返回 `{"code": ..., "message": ..., "data": ...}`。
  - **创建类接口用 201**，查询 / 动作类用 200。
  - 列表接口统一返回 `{list, total, page, pageSize}`，按 `created_at desc, id desc` 排序。
- 所有业务路由通过 `dependencies=[Depends(get_current_user)]` 启用鉴权。
- 列表查询统一暴露 `status`、`page`、`pageSize`（alias）分页参数，用 `Query(default=..., ge=..., le=...)` 约束。
- 前后端通过 `CamelModel` 统一 camelCase 契约；状态机动作走子资源路径（如 `/api/inbound-orders/{id}/receive`），
  不在请求体里塞状态字段。

## 4. 提交前必须运行（全绿才可提交）

```bash
# 后端单测（不连真实数据库）
cd backend-python; uv run pytest

# 前端单测（vitest）+ 构建（含 vue-tsc 类型检查）
cd frontend-vue; npm test; npm run build

# 涉及核心链路改动时补跑 E2E
cd frontend-vue; npm run test:e2e

# 动过 models/ 里的列类型时必跑（create_all 不会 ALTER，没这一步等于没改）
cd backend-python; $env:DATABASE_URL="..."; uv run alembic upgrade head
uv run python scripts/check_money_columns.py   # 问数据库本身，而不是问迁移命令的退出码
```

- 用例数量不在本文件维护（它会腐烂）；以 `uv run pytest` 的实际输出为准。
- 财务不变量（借贷平衡、试算恒等、幂等、锁账拒写）必须有对应测试；覆盖率基线只升不降。
- 金额一律 `Numeric(18,2) + Decimal`，**禁止浮点**：统一经 `app/common/money.py` 的 `money()`
  量化（`ROUND_HALF_UP`，不是 Python `round()` 的银行家舍入），比较用精确相等，**不得用容差兜浮点残差**。
  `Decimal` 与 `float` 混算是 `TypeError`，不是精度问题，所以聚合结果（`func.sum`）也必须过 `money()`。
- **持久库列结构变更必须有 Alembic 迁移**（`backend-python/migrations/versions/`）。
  `app/main.py` 启动时的 `Base.metadata.create_all` 只建缺失的表，**不会 ALTER 已存在的列**；
  只改模型不写迁移，等于新库和测试库对了、线上与本地 `psi_fin.db` 仍是旧类型。
  迁移只从 `DATABASE_URL` 取串，缺省即报错退出，不静默回退 SQLite。
- **单测跑在 SQLite 上（`tests/conftest.py`），`SELECT ... FOR UPDATE` 被静默忽略**；不设
  `DATABASE_URL` 时本地开发也是 SQLite（`app/database.py` 默认 `psi_fin.db`）。本地 compose
  是 MySQL 8.0，线上真后端演示是 Vercel Serverless + Neon PostgreSQL（`render.yaml` 为备选）。
  并发与锁、以及列类型约束，以 SQLite 绿的测试为证据等于没有证据，须在 MySQL/PostgreSQL 上复现。

## 5. Seam 纪律（写测试之前）

**Seam** 是观察行为而不伸手进实现的公共边界。本项目的 seam 就是 service 层入口
（`inventory_service.add_stock` / `deduct_stock` 等）与 HTTP 响应契约；测试打在 seam 上，
不打在内部实现上。

- **新增**公共 seam（新 service 入口、新 HTTP 契约）在写测试前先列出它并向用户确认；
  对**已有 seam** 补测试、以及诊断流程里的回归测试（`diagnosing-bugs` Phase 5）无需确认，直接写。
- 优先一 cycle 一 seam 一测试：先 red 后 green，不无目的地横向铺测试；
  但上一节列出的财务不变量（借贷平衡/幂等/锁账拒写）属于必须成套覆盖的，允许一次补齐多个 seam。
- 优先复用已存在的 seam；确需新增时选在尽可能高的位置，跨项目 seam 越少越好。
- 命名用业务术语表（`.qoder/repowiki/knowledge/zh/业务术语表/`）的词，使测试名读起来像规格。

## 6. 配套的 agent skills

`.qoder/skills/` 下三个 model-invoked skill，会在对应场景自动触发，也可显式调用：

| Skill | 何时用 |
|---|---|
| `grilling` | 动手前把设计决策问完、问到底，收敛到没有隐含假设。与 `/opsx:explore`（发散探索）互补 |
| `code-review` | 双轴评审：Standards 轴以本文件为事实源，Spec 轴以 `openspec/changes/<name>/` 为事实源；默认评审未提交的工作区改动，也可给 `<fixed point>` 评审已提交区间 |
| `diagnosing-bugs` | 难 bug / 性能回退：先建 tight 且 red-capable 的反馈回路，才允许提假设 |

评审与诊断的判定标准以本文件为准；本文件与 skill 冲突时，改本文件，不要在各 skill 里重复一套规则。

