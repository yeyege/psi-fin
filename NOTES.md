# NOTES — WMS 测试开发说明

## 技术栈选择

- **后端**：Python 3.11+ / FastAPI / SQLAlchemy 2.0 / SQLite（开发库 wms.db）
- **前端**：Vue 3 + Element Plus + TypeScript + Vite
- **测试**：后端 pytest（16 用例）+ 前端 vitest（12 用例）

选择理由：FastAPI 代码简洁、迭代快；Element Plus 的 `el-form`/`el-select`/`el-table`/`el-pagination` 组件契合入库表单与库存列表需求；SQLite 文件库零配置，便于「一键启动」。

---

## 一、AI 工具使用情况

**使用工具**：Trae（GLM-5.2）作为全程协作的 AI 助手。

**如何使用**：

1. **理解需求**：先自行通读 README / TASKS / API_SPEC / 模板代码，画出数据流，再让 AI 在此基础上生成代码。
2. **生成样板代码**：让 AI 按 API_SPEC 生成 Service 层与路由，并明确要求「事务边界、异常处理、camelCase 字段」。
3. **代码审查**：AI 生成后逐段审查事务一致性、异常分支、边界条件，手动补充遗漏（如分页排序稳定性）。
4. **测试生成**：让 AI 为 Service 层生成单元测试，再手动补齐超卖、回滚、合并扣减等边界用例。
5. **调试辅助**：浏览器端到端验证时，用 AI 辅助分析 el-select 自定义下拉点击被拦截的问题，改用 DOM 直接触发。

**AI 帮我解决的一个具体问题**：
前后端命名风格不一致——后端 Pydantic 默认 snake_case（`supplier_name`），而 API_SPEC 与前端 TS 接口约定 camelCase（`supplierName`），Pydantic v2 默认不接受 camelCase 输入会直接 422。AI 建议用 `alias_generator=to_camel` + `populate_by_name=True` 的 `CamelModel` 基类统一解决，输入输出同时兼容，避免了逐字段加 alias 的繁琐。

**AI 生成代码的一个问题及修复**：
AI 初版的库存查询分页只按 `updated_at DESC` 排序。单元测试暴露了问题——当多条记录的 `updated_at` 相同（同批插入）时，排序不确定，导致跨页数据重叠。我发现了这个问题，修复为 `updated_at DESC, id DESC` 加二级排序键保证分页稳定，并补充了对应的回归测试。

---

## 二、任务 3 — Bug 说明

### Bug 1（后端）：商品删除未校验关联库存

- **位置**：`backend-python/app/routers/products.py` `delete_product`
- **现象**：原实现直接 `db.delete(product)`，未检查该商品是否仍有库存记录。删除后 `inventory` 表中 `product_id` 指向已删除商品，库存数据孤立，且外键约束在 SQLite 默认未启用时不会报错，问题隐蔽。
- **修复**：删除前查询 `inventory` 表中 `product_id = ? AND quantity > 0` 的记录数，若 >0 则返回 400 并提示具体库存条数，拒绝删除。

### Bug 2（前端）：商品列表编辑后跳回第 1 页

- **位置**：`frontend-vue/src/views/ProductsView.vue` `handleSubmit`
- **现象**：原实现无论新增还是编辑，提交后都执行 `currentPage.value = 1`，导致用户在第 N 页编辑某商品返回列表时被强制跳回第 1 页，丢失浏览位置。
- **修复**：仅新增时跳到第 1 页（新记录通常在首页）；编辑时保留当前页码，重新加载列表数据。

---

## 三、选做 A — 出库单并发安全方案

**场景**：出库需先校验库存充足再扣减，高并发下要防止「超卖」。

**方案：原子条件 UPDATE（乐观式 CAS 语义）**

对每条出库明细执行单条 SQL：

```sql
UPDATE inventory
   SET quantity = quantity - :q
 WHERE product_id = :pid
   AND location_code = :loc
   AND quantity >= :q        -- 关键：扣减前置校验合并进同一条语句
```

通过 `rowcount` 判断结果：`0` 表示库存不足或库存行不存在 → 抛 409，整单回滚。

**方案理由**：

- **消除竞态**：把「检查库存充足」与「扣减」合并为一条原子 UPDATE，数据库会对该行加行锁，彻底消除「先查后扣」的 TOCTOU 窗口。
- **无需重试**：相比版本号乐观锁（需 version 列 + 冲突重试），本方案一条 SQL 完成，无重试逻辑，更简洁。
- **跨数据库可迁移**：该写法对 PostgreSQL/MySQL 同样适用，迁移无成本。
- **不选用悲观锁**：`SELECT ... FOR UPDATE` 在 SQLite 支持有限，且会降低并发吞吐，对 WMS 这类读多写少场景不划算。

**整单一致性**：整个出库单在单个事务内，任一明细扣减失败则全部回滚，不会出现「部分明细已扣减、单据却未创建」的中间态（已有 `test_outbound_atomic_rollback_on_partial_failure` 测试覆盖）。

---

## 四、选做 B — 单元测试

- **后端**（pytest，16 用例，全部通过）：
  - `tests/test_inbound_service.py`：入库单创建——库存累加、新建库存行、同(商品,库位)合并、商品/库位不存在异常、单号递增。
  - `tests/test_outbound_service.py`：出库扣减、超卖防护(409)、库存行不存在、商品不存在、合并扣减、部分失败整单回滚。
  - `tests/test_inventory_service.py`：keyword 模糊搜索、仓库筛选、分页不重叠、camelCase 字段。
- **前端**（vitest，12 用例，全部通过）：
  - `src/utils/inventory.test.ts`：`isLowStock` 边界值、`filterByKeyword`（名称/SKU/大小写/空）、`filterByWarehouse`、`lowStockRowClass`。
  - 将低库存判定与筛选逻辑抽离为纯函数 `src/utils/inventory.ts`，便于测试与复用。

运行方式：
- 后端：`cd backend-python && uv run pytest`
- 前端：`cd frontend-vue && npm test`

---

## 五、选做 C — 前端性能优化

库存列表页采用以下优化（数据量 500+ 时不会卡顿）：

1. **后端分页**：列表只请求当前页（默认 20 条），DOM 中最多渲染 20 行，避免一次性渲染 500+ 行造成的卡顿。
2. **搜索防抖**：关键词输入停止 300ms 后才发请求，减少输入过程中的无效 API 调用。
3. **筛选逻辑抽离为纯函数**：`src/utils/inventory.ts`，便于后续在虚拟滚动等场景复用。

> 数据库层面：`inventory` 表对 `location_code`、`product_id` 建立索引，JOIN 查询走索引，避免全表扫描。

---

## 六、遇到的问题与解决

1. **前后端字段命名不一致**：见上文 AI 使用部分，用 `CamelModel` 基类统一 camelCase。
2. **分页排序不稳定**：见上文，加 `id` 二级排序键。
3. **Vite dev 进程在 Windows 偶发崩溃**（`STATUS_STACK_BUFFER_OVERRUN`）：重启即可，未影响代码正确性；生产构建 `npm run build` 不受影响。
4. **Element Plus el-select 自定义下拉点击被拦截**：端到端测试时，浏览器自动化点击 combobox ref 命中内层 `<span>`。解决：改用 `evaluate` 直接触发 `.el-select__wrapper` 的 click 与选项 click，符合真实用户交互路径。
5. **init_data 不会自动执行**：原模板需手动 `python init_data.py` 才有数据。改为在 `main.py` 的 `lifespan` 启动钩子中调用，实现真正的「一键启动即可看到完整功能」。

---

## 七、如果有更多时间

- **入库/出库单列表与详情页**：后端接口已实现，前端可补列表页 + 详情查看 + 单据状态流转（DRAFT → COMPLETED）。
- **库存盘点 / 库存调整**：支持负库存修正、盘点单。
- **出库并发压测**：用 `locust` 或 `asyncio` 并发脚本验证原子 UPDATE 在高并发下的超卖防护与吞吐。
- **数据库迁移**：引入 Alembic（已装依赖）做版本化 schema 迁移，替代 `create_all`。
- **部署与 CI**：Docker Compose 一键拉起前后端 + PostgreSQL；GitHub Actions 跑测试与构建。
- **前端**：补充虚拟滚动组件（如 `el-table-v2`）应对单页超大列表；接入 Pinia 做状态管理；增加 E2E 测试（Playwright）。
- **安全**：接入 JWT 鉴权、操作审计日志、接口限流。

---

## 八、提交检查清单

- [x] 必做任务 1（入库单创建）后端 + 前端完成
- [x] 必做任务 2（库存查询）后端 + 前端完成
- [x] 必做任务 3（2 个 Bug）定位并修复
- [x] 选做 A（出库单 + 并发安全）完成
- [x] 选做 B（单元测试）后端 16 + 前端 12 用例
- [x] 选做 C（前端性能优化）后端分页 + 防抖
- [x] 一键启动：后端 `uv run uvicorn app.main:app --reload`（自动建表+种子数据）；前端 `npm run dev`
- [x] Git 提交记录清晰（小步提交）
- [x] NOTES.md 已填写
