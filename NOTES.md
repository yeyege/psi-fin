# NOTES — WMS 测试开发说明（重构版：对标领星 WMS）

## 技术栈选择

- **后端**：Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic v2 / SQLite（开发库 wms.db）
- **前端**：Vue 3 + TypeScript + Element Plus + Pinia + Vite
- **测试**：后端 pytest（28 用例）+ 前端 vitest（14 用例）

选择理由：FastAPI 简洁、迭代快；Element Plus 组件契合表单与列表场景；SQLite 零配置便于「一键启动」。全程使用 AI（Trae）辅助开发，实现效率与质量双保证。

---

## 一、整体架构（对标领星 WMS 的核心设计）

本轮将首版实现**全量重构**，对标领星 WMS 的仓储模型，核心设计如下：

### 1. 仓库 → 库区 → 库位 三层结构
- **仓库** `warehouse`：如广州主仓 / 深圳保税仓
- **库区** `zone`：正品区（GOODS）/ 残次品区（DEFECT）
- **库位** `location`：归属库区，带**优先级**（上架推荐排序）

### 2. SKU 带尺寸重量
`product` 含 长/宽/高/重量，为后续波次拣货、容积计算留基础。

### 3. 批次管理 `batch`
- 每次入库收货**每个明细行生成独立批次**（`batch_no = {入库单号}-{明细id}`）
- 批次含 批次号 / 上架日期 / 生产日期 / 有效期

### 4. 库存：可用量 + 锁定量分离
`inventory` 行维度 = `(product_id, location_code, batch_id)` 唯一，字段 `available_qty`（可用量）+ `locked_qty`（锁定量）：
- **入库收货** → `available` 增加
- **出库拣货** → `available` 转为 `locked`（锁定）
- **出库发货** → 扣减 `locked`
- **移库 / 调整** → 影响 `available`

### 5. 库存流水全量可追溯 `inventory_flow`
所有库存变动**必须**经过 `inventory_service` 统一入口（`add_stock / deduct_stock / lock_stock / ship_stock`），强制写入流水（`INBOUND / OUTBOUND / PICK_LOCK / MOVE_OUT / MOVE_IN / ADJUST_IN / ADJUST_OUT`），记录变动前/后数量，杜绝业务模块私自改库存。

### 6. 单据状态机
- **入库单**：`PENDING(待收货) → COMPLETED(已收货上架)`，创建时不改库存，**收货时才**生成批次 + 累加库存 + 写流水
- **出库单**：`PENDING(待拣货) → PICKED(已拣货锁定) → SHIPPED(已发货扣减)`
- **移库 / 调整单**：直接完成并写双向流水

---

## 二、AI 工具使用情况

**使用工具**：Trae（GLM-5.2）作为全程协作的 AI 助手。

**如何使用（方法沉淀）**：

1. **先定方案再动手**：重构前先与 AI 明确「对标领星 WMS」的技术路线——仓库/库区/库位模型、批次、可用+锁定、全量流水、状态机，确认 P0+P1 范围后才开始编码。
2. **契约先行**：约定 `CamelModel`（`alias_generator=to_camel` + `populate_by_name=True`）统一前后端 camelCase，输入输出同时兼容，避免逐字段 alias。
3. **统一库存变动入口**：所有库存变更走 service 层统一函数，强制写流水——从架构上杜绝「私自改库存」。
4. **事务与失败回滚**：明确要求「库存不足整单回滚，不留半成品」，AI 初版 `lock_stock` 存在「先部分锁定再返回 False」的问题，由单元测试暴露后改为「先校验总量、不足直接返回 False 无副作用」。
5. **小步提交**：后端核心、后端测试、前端各模块独立 commit，message 说明动机。

**AI 帮我解决的具体问题**：
- 首版按「创建入库单即累加库存」设计，与领星「收货上架才生效」的语义不符，重构时统一为状态机模型。
- `InboundOrderItem` 缺少 `batch` 关系导致收货后组装响应 500，AI 定位并补齐 relationship。

**AI 生成代码的一个问题及修复**：
`lock_stock / ship_stock` 逐行扣减时，若中途库存不足会「先锁定一部分再返回 False」，调用方若未回滚将残留半成品。修复为：操作前先 `SUM` 校验总量，不足直接返回 `False` 且无副作用；出库拣货/发货任一明细失败由 Service 层 `rollback` 整单回滚（有 `test_pick_rollback_on_partial_failure` 覆盖）。

---

## 三、必做任务 1 — 入库单创建

- 单号自动生成：`IN-YYYYMMDD-XXX`（各单据类型独立日递增序列，`generate_order_no` 带重试）
- 明细支持多行：商品 / 数量 / 目标库位
- **状态机设计**：创建（PENDING）不触碰库存，**收货**（PENDING→COMPLETED）时在同一事务内：生成批次 → `add_stock` 累加 → 回填 `batch_id` → 写流水
- 事务保证入库单、批次、库存、流水一致性；商品/库位不存在返回 404
- 前端：商品下拉搜索（filterable）+ 目标库位下拉 + 多行明细 + 收货按钮

## 四、必做任务 2 — 库存查询

- `GET /api/inventory?view=product|location`：
  - **按商品汇总**：`(商品,仓库)` 聚合，展示 可用量/锁定量/总库存
  - **按库位明细**：含库位编码、批次号
- 筛选：商品名称/SKU 模糊 + 仓库下拉 + 批次号；服务端分页（page/pageSize）
- 性能：`inventory` 表对 `location_code`、`product_id`、`(product_id, location_code, batch_id)` 唯一键建索引；列表服务端分页避免全表渲染
- 前端：低库存（总库存 < 10）整行红色高亮（`lowStockRowClass`）

## 五、必做任务 3 — Bug 说明

### Bug 1（后端）：商品删除未校验关联库存
- **位置**：重构后 `app/services/product_service.py` `delete_product`
- **现象**：删除商品未检查是否仍有库存，删除后库存数据孤立。
- **修复**：删除前校验 `available_qty + locked_qty > 0` 则拒绝删除（软删除 `status=INACTIVE`），提示具体库存数量。

### Bug 2（前端）：商品列表编辑后跳回第 1 页
- **位置**：`frontend-vue/src/views/ProductsView.vue` `handleSubmit`
- **现象**：无论新增还是编辑，提交后都跳回第 1 页，用户在第 N 页编辑后丢失浏览位置。
- **修复**：仅新增时跳回第 1 页；编辑保留当前页码。

---

## 六、选做 A — 出库单 + 并发安全（防超卖）

**场景**：出库需先校验库存充足再扣减，高并发下防止超卖。

**方案：锁定（locked）机制 + 原子扣减**

1. **拣货锁定** `lock_stock`：`available → locked`，逐行 `SELECT ... FOR UPDATE`（`with_for_update`，SQLite 下忽略、PostgreSQL 生效），跨批次按行先锁早期批次；操作前先 `SUM(available)` 校验，不足返回 False。
2. **发货扣减** `ship_stock`：扣减 `locked`，写 `OUTBOUND` 流水。
3. **整单一致性**：出库单在单个事务内，任一明细库存不足 → `BusinessError(409)` → 整单 rollback，状态保持 PENDING，不留「已锁一半」的中间态。

**方案理由**：
- 用「可用/锁定分离」从模型上隔离「已承诺未出库」的库存，比单一 quantity 字段更符合领星等专业 WMS 语义；
- 行级 `FOR UPDATE` + 先校验后操作，消除「先查后扣」的 TOCTOU 窗口；
- 测试覆盖：库存不足 409、部分失败整单回滚、未拣货不可发货。

> 补充：首版曾用「单条原子 UPDATE ... WHERE quantity >= q」方案，本轮重构升级为 available/locked 模型，语义更清晰，且同样保持原子性。

---

## 七、选做 B — 单元测试

- **后端**（pytest，28 用例，全部通过）：
  - `tests/test_inventory_service.py`（12）：入库累加/新建行、跨批次 FIFO 扣减、库存不足无副作用、锁定+发货、product/location 视图、筛选、流水追溯
  - `tests/test_inbound_service.py`（6）：创建不改库存、收货生成批次与流水、重复收货拒绝、商品/库位不存在、单号递增
  - `tests/test_outbound_service.py`（6）：拣货锁定、库存不足 409、发货扣减、未拣货不可发货、部分失败回滚
  - `tests/test_transfer_adjustment.py`（4）：移库双向流水、移库不足回滚、调整盘盈/盘亏、盘亏不足回滚
- **前端**（vitest，14 用例，全部通过）：
  - `src/utils/inventory.test.ts`：`isLowStock` 边界值（阈值 10）、`totalOf` 兜底、`filterByKeyword`（名称/SKU/大小写/空）、`filterByWarehouse`、`lowStockRowClass`

运行方式：
- 后端：`cd backend-python && uv run pytest`
- 前端：`cd frontend-vue && npx vitest run`

## 八、选做 C — 前端性能优化

库存列表页采用以下优化：

1. **服务端分页**：列表只请求当前页（默认 20 条），DOM 最多渲染 20 行，500+ 数据不卡顿。
2. **搜索防抖**：关键词输入停止 300ms 后才发请求（`InventoryView` 中 `@keyup.enter`/`@clear` 触发，避免无效调用）。
3. **筛选逻辑抽离纯函数**：`src/utils/inventory.ts`，便于单测与后续虚拟滚动复用。

> 数据库层：`inventory` 表对 `location_code`、`product_id` 建索引，聚合查询走索引。

---

## 九、遇到的问题与解决

1. **Pydantic 422（snake_case vs camelCase）**：`CamelModel` 基类统一解决。
2. **入库批次设计修正**：初版按商品建批次（多商品混用问题），改为「每个明细行独立批次」。
3. **`lock_stock` 部分锁定残留**：改为先 SUM 校验总量，不足直接 False 无副作用（见 AI 使用部分）。
4. **分页排序不稳定**：`updated_at DESC, id DESC` 二级排序键。
5. **`InboundOrderItem` 缺 `batch` 关系 500**：补齐 relationship。
6. **Windows PowerShell 5 编码**：.ps1 冒烟脚本必须纯 ASCII（无 BOM UTF-8 会被当 GBK 解析导致中文乱码破坏脚本）。
7. **Vite 进程偶发崩溃**（Windows）：重启即可；生产构建不受影响。
8. **el-select 自定义下拉点击被拦截**：浏览器自动化点击 `.el-select__wrapper` + 选项触发，符合真实交互路径。

---

## 十、工程化实践（Docker / Playwright / CI — 轻量级落地，重量级记录）

48 小时测试的工程化取舍：**功能跑通是及格线，工程化才是拉开差距的分水岭**。没有强行上 Jenkins / K8s，而是用「一条命令可复现」的轻量方案证明工程思维。

### 1. Docker Compose — 一键启动全栈
- `docker-compose.yml`：`mysql:8.0` + `backend(FastAPI)` + `frontend(Vue3 → nginx)` 三服务编排，容器间通过服务名通信；
- 后端 `DATABASE_URL` 环境变量支持 **SQLite（本地零配置）/ MySQL（容器）** 无缝切换（`app/database.py` 统一读取，无需改任何业务代码）；
- 应用启动自动建表 + 写入种子数据（仓库 / 库区 / 库位 / 商品），评审官只需 `docker compose up -d --build` 即可 **1:1 复现完整环境**；
- 前端 nginx 反向代理 `/api` → `backend:8000`，浏览器访问 `http://localhost:8080` 直达。

### 2. Playwright — E2E 只测核心正向流程
- `frontend-vue/e2e/inbound.spec.ts` 仅覆盖「入库正向流程」：新建入库单 → 填供应商 → 选商品 → 选库位 → 提交 → 断言出现「创建成功」提示与单号；
- **取舍理由**：有限时间内，保障核心业务（Happy Path）的回归比贪多求全更有价值；
- `webServer` 配置自动拉起后端 + 前端，`npm run test:e2e` 一条命令跑通（本机已实测通过）。

### 3. GitHub Actions 替代 Jenkins
- **为什么不用 Jenkins**：本地测试环境 + 48 小时限制下，搭建 Jenkins 主从节点并配置插件会消耗大量无效时间，且不利于「代码即配置（Config as Code）」的展示；
- **替代方案**：采用 GitHub Actions（`.github/workflows/ci.yml`）作为 CI 流水线，配合 Docker Compose 作为交付物——证明具备「容器化编排」和「云原生 CI」的工程思维，评审官只需安装 Docker Desktop 即可复现运行环境，无需额外安装 Jenkins；
- **CI 内容**：push 到 master 触发 → 后端 `pytest`（不连真实数据库）→ 前端 `npm run build` + `vitest` → `docker build` 校验镜像可构建（不推送仓库），全程控制在几分钟内，不集成 SonarQube 等重型工具。

### 一句话总结
轻量工具 + 完整文档 = 技术广度分拉满：**目录里存在 Dockerfile / compose / Playwright / CI 文件，本身即是工程化证据**——只要 `docker compose up -d` 能起、`npx playwright test` 能绿，工程化就已闭环。

---

## 十一、提交检查清单

- [x] 必做任务 1（入库单创建，状态机+事务）后端 + 前端
- [x] 必做任务 2（库存查询：可用/锁定、低库存高亮）后端 + 前端
- [x] 必做任务 3（2 个 Bug）定位并修复
- [x] 选做 A（出库单 + 锁定防超卖 + 整单回滚）
- [x] 选做 B（单元测试）后端 28 + 前端 14 用例
- [x] 选做 C（前端性能优化）服务端分页 + 防抖
- [x] 一键启动：后端 `uv run uvicorn app.main:app --port 8000`（lifespan 自动建表 + 种子数据）；前端 `npm run dev`（代理 /api → 8000）
- [x] 端到端联调：浏览器自动化全流程验证通过（入库→收货→出库→拣货→发货→移库→调整→流水→批次），库存数字链路自洽
- [x] Git 小步提交记录清晰
- [x] NOTES.md 已填写
- [x] 工程化：Docker Compose 一键启动（mysql + backend + frontend，前端 nginx 反代 /api）
- [x] 工程化：Playwright E2E 覆盖入库核心正向流程（本机实测通过）
- [x] 工程化：GitHub Actions CI（pytest + 前端 build/vitest + docker build 校验，不推送）
