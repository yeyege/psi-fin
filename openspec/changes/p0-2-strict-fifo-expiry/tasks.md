## 1. 后端：批次生命周期状态计算

- [x] 1.1 在 `backend-python/app/services/inventory_service.py` 增加生命周期阈值常量（`EXPIRY_WARN_DAYS = 30`、`AGING_DAYS = 180`）与纯函数（入参 batch/日期，返回 `batchStatus`、`daysToExpiry`、`ageDays`，枚举 NORMAL / EXPIRING / EXPIRED / AGING，日期为空时对应字段为 None）。验证：`cd backend-python && uv run pytest` 新增用例 `tests/test_batch_expiry.py::test_batch_status_calculations` 通过
  - 完成记录（2026-10-04）：实现为 `batch_lifecycle(batch, now=None) -> BatchLifecycle`。返回值用 `NamedTuple` 而非裸三元组，因为 3.1/3.2 两个查询点共用时靠位置对齐易错。口径上有一条 spec 隐含的互斥关系：**呆滞只对未设有效期的批次成立**，已设有效期但库龄超 180 天的老批次走有效期分支，不得同时被判成临期与呆滞；已单独用一个用例锁住。边界归属：30 天含、超过 180 天才算呆滞、有效期正好今日仍属临期。取证：`tests/test_batch_expiry.py` 3 例全绿（全量 145 passed）。本组未动查询与扣减排序

## 2. 后端：扣减候选按效期优先排序（三入口共用）

- [x] 2.1 抽出共享排序 helper（outerjoin Batch，排序键 = 无批次行置后 → COALESCE(expiry, manufacture, inbound) ASC → Batch.id/Inventory.id 稳定序），并让 `deduct_stock` / `lock_stock` / `ship_stock` 三处循环取候选行时统一使用该排序。验证：既有 `tests/test_inventory_service.py` 全部通过（无日期差异批次仍先扣早期批次）
  - 完成记录（2026-10-07）：实现为模块常量 `FEFO_ORDER_KEYS`（四键元组），三入口各自 `outerjoin(Batch, Inventory.batch_id == Batch.id)` + `order_by(*FEFO_ORDER_KEYS)`；无有效期退回生产日期、再无退回入库日期由一条 `COALESCE` 覆盖（D1）
  - ⚠ **必须 `with_for_update(of=Inventory)`，不是风格选择**：排序键取自批次表就得外连接 Batch，而 PostgreSQL 禁止对 LEFT JOIN 的可空侧加行锁（`FOR UPDATE cannot be applied to the nullable side of an outer join`）。裸 `with_for_update()` 在 SQLite 下被忽略、单测全绿，上 PG 直接报错 —— 正是 AGENTS.md §4 说的「以 SQLite 绿的测试为证据等于没有证据」
  - 方言差异（已知、不绕行，待在真实库复现）：按 PG/MySQL 方言编译核对，PG 渲染 `FOR UPDATE OF inventory`（窄锁，符合预期）；**MySQL 方言将 `of` 丢弃、渲染裸 `FOR UPDATE`**，即 compose 里那台 MySQL 8 会连 `batches` 侧一起锁。只影响锁范围、不影响防超卖语义（逐行扣减的原子性仍由「条件 UPDATE + 失败重读重试」保证）；D17 已定主库切 PG、MySQL 降为兼容选项，故不为此加标量子查询绕行
- [x] 2.2 新增 FEFO 用例：显式构造两批次（B 有效期早于 A 且 A 先入库），扣减后断言先扣尽 B；构造「无有效期 → 退回生产日期」与「无批次行最后扣」用例。验证：`uv run pytest tests/test_batch_expiry.py` 通过
  - 完成记录（2026-10-07）：`tests/test_batch_expiry.py` 新增 3 例，均打在 `deduct_stock` 这个已有 seam 上。三例都刻意把「建库存行先后」与「应扣先后」做成相反（无批次行先建、应扣批次后建）：否则旧排序恰好也能得出同样结果，用例会假绿。先跑 red（3 failed / 3 passed）再改实现，后跑 green：全量 **148 passed**（原 145 + 3）；`test_deduct_stock_cross_batch_fifo`（两批次同日建立）原断言仍成立，靠的是键 3/4 的稳定序
  - 未覆盖项：`lock_stock` / `ship_stock` 的排序本轮只共用实现、没有专属断言，「拣货与发货同序」的回归由组 4（tasks 4.1）负责

## 3. 后端：查询接口扩展字段与状态筛选

- [ ] 3.1 `query_inventory`（view=location）每行增加 `manufactureDate` / `expiryDate` / `daysToExpiry` / `ageDays` / `batchStatus`（沿用 joinedload 或 outerjoin Batch 取日期字段，避免 N+1）。验证：`uv run pytest` 新增 location 视图断言返回新字段用例通过
- [ ] 3.2 `query_batches` 每行增加 `ageDays` / `batchStatus`；router `GET /api/inventory/batches` 增加可选 `status` 参数（缺省返回全部），service 按状态过滤。验证：`uv run pytest` 新增「status=EXPIRING 只返回临期批次」「缺省返回全部」用例通过

## 4. 后端：发货与拣货同序回归

- [ ] 4.1 新增出库场景用例：拣货后发货，断言发货扣减批次的顺序与拣货锁定一致（构造多有效期批次跨单验证）。验证：`uv run pytest tests/test_outbound_service.py` 新增用例通过

## 5. 前端：类型扩展与预警展示

- [ ] 5.1 扩展 `frontend-vue/src/api/index.ts`：`InventoryRow` location 视图字段与 `BatchRow` 增加 `manufactureDate?/expiryDate?/daysToExpiry?/ageDays?/batchStatus?`；新增 `getBatches` 的 `status` 参数。验证：`cd frontend-vue && npx vue-tsc --noEmit` 无类型错误
- [ ] 5.2 `BatchesView.vue`：新增「状态」列（el-tag：NORMAL→success、EXPIRING→warning、EXPIRED→danger、AGING→warning）与状态筛选下拉（绑定 `getBatches` status 参数）。验证：`npx vitest run` 通过；手动打开批次页筛选「临期」仅显示对应批次
- [ ] 5.3 `InventoryView.vue`：location 视图新增「有效期至/批次状态」列与状态 Tag（缺字段显示 "-"）。验证：手动在库存页切到「库位明细」视图，能看到批次状态列

## 6. 集成验证与回归

- [ ] 6.1 全量回归：后端 `cd backend-python && uv run pytest`（99+ 新增用例全绿），前端 `cd frontend-vue && npx vitest run` 全绿；`npm run build` 成功。验证：两条命令 0 失败
- [ ] 6.2 端到端冒烟：一键启动后浏览器走通「两批不同效期入库 → 出库拣货 → 发货」，观察库存明细与流水：先扣临期批次，批次页状态 Tag 正确（临期/正常）。验证：实际操作无报错且扣减批次符合 FEFO 预期
- [ ] 6.3 更新 `NOTES.md`：P0-2 标记完成，补充方案说明与测试数量。验证：NOTES.md 该节内容与实际实现一致
