## 1. 后端：批次生命周期状态计算

- [ ] 1.1 在 `backend-python/app/services/inventory_service.py` 增加生命周期阈值常量（`EXPIRY_WARN_DAYS = 30`、`AGING_DAYS = 180`）与纯函数（入参 batch/日期，返回 `batchStatus`、`daysToExpiry`、`ageDays`，枚举 NORMAL / EXPIRING / EXPIRED / AGING，日期为空时对应字段为 None）。验证：`cd backend-python && uv run pytest` 新增用例 `tests/test_batch_expiry.py::test_batch_status_calculations` 通过

## 2. 后端：扣减候选按效期优先排序（三入口共用）

- [ ] 2.1 抽出共享排序 helper（outerjoin Batch，排序键 = 无批次行置后 → COALESCE(expiry, manufacture, inbound) ASC → Batch.id/Inventory.id 稳定序），并让 `deduct_stock` / `lock_stock` / `ship_stock` 三处循环取候选行时统一使用该排序。验证：既有 `tests/test_inventory_service.py` 全部通过（无日期差异批次仍先扣早期批次）
- [ ] 2.2 新增 FEFO 用例：显式构造两批次（B 有效期早于 A 且 A 先入库），扣减后断言先扣尽 B；构造「无有效期 → 退回生产日期」与「无批次行最后扣」用例。验证：`uv run pytest tests/test_batch_expiry.py` 通过

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
