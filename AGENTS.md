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
- **每一次库存变动强制写入 `inventory_flow` 流水**，并以 `FLOW_TYPE_*` / `ORDER_TYPE_*` 常量标注类型。
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
# 后端单测（126 用例，不连真实数据库）
cd backend-python; uv run pytest

# 前端单测（31 用例，vitest）+ 构建（含 vue-tsc 类型检查）
cd frontend-vue; npm test; npm run build

# 涉及核心链路改动时补跑 E2E
cd frontend-vue; npm run test:e2e
```

- 财务不变量（借贷平衡、试算恒等、幂等、锁账拒写）必须有对应测试；覆盖率基线只升不降。
- 金额一律 `Numeric(18,2) + Decimal`，**禁止浮点**，借贷平衡用精确比较。
