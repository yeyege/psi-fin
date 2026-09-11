## Why

当前库存扣减（`deduct_stock` / `lock_stock` / `ship_stock`）跨批次时一律按 `Inventory.id`（≈建批/入库先后）顺序先出，虽满足近似 FIFO，但完全未利用批次已存的 `manufacture_date` / `expiry_date`：到期最近的批次可能滞留到最后才被扣，且系统对临期、已过期、长库龄（呆滞）批次没有任何预警能力。这直接对应 NOTES.md P0-2 目标——降「长库龄物料占比」、控「效期风险」，让「先到期先出（FEFO）」真正落地。

## What Changes

- **库存扣减顺序升级为「效期优先 + 严格 FIFO」**：`inventory_service` 三个扣减入口（出库拣货 `lock_stock`、发货扣减 `ship_stock`、移库/调整/盘亏 `deduct_stock`）跨批次取行顺序从 `Inventory.id` 改为按批次的 `expiry_date ASC（先到期先出）→ manufacture_date ASC → Batch.inbound_date ASC → Inventory.id ASC` 复合排序；无批次的库存行最后扣减，全规则下不足才返回 `False`。
- **查询响应扩展效期与状态字段**：库存 `view=location` 明细与批次列表接口新增返回 生产日期 / 有效期至 / 距到期天数 / 库龄天数 / 批次状态标记（正常 / 临期 / 已过期 / 呆滞）。
- **批次状态标记支持筛选**：批次列表支持按状态（临期 / 已过期 / 呆滞）过滤，为前端预警视图提供数据。
- **前端展示预警**：库存（库位明细）与批次管理页展示状态 Tag（临期黄 / 过期红 / 呆滞橙），批次汇总 Mock 卡片替换为真实状态计数（沿用视图汇总卡组件）。
- **测试契约同步**：更新既有「跨批次先扣早期批次」断言为按效期排序；新增 FEFO / 无效期回退 FIFO / 无批次行最后扣 / 发货与拣货同序 / 状态标记计算等用例。

## Capabilities

### New Capabilities

- `inventory/batch-expiry`: 定义库存扣减的批次选择顺序（效期优先 + FIFO 回退链）、批次生命周期状态（正常 / 临期 / 已过期 / 呆滞）的计算口径，以及库存/批次查询中这些字段与状态筛选的返回契约。覆盖出库拣货、发货、移库、调整、盘点盘亏全部扣减路径与对应查询接口。

### Modified Capabilities

（无。本 change 新增能力契约；仓库现有主规格为空，不修改既有 capability 文件。）

## Impact

- **后端行为变化**：`backend-python/app/services/inventory_service.py` 中 `deduct_stock` / `lock_stock` / `ship_stock` 的批次取序逻辑变更（不改变函数签名与调用方接口，但影响扣减结果选中的批次 → 相关单测断言需同步）。跨批次扣减结果会与旧逻辑不同，属**行为级变更**（不是 REST 契约破坏，单号/状态机/流水格式均不变）。
- **API 响应扩展**：`GET /api/inventory?view=location` 明细、`GET /api/inventory/batches` 新增只增字段与状态筛选参数，向后兼容（新字段可选展示，老客户端不受影响）。
- **数据模型**：复用 `Batch` 现有 `manufacture_date` / `expiry_date` / `inbound_date`，无表结构迁移。
- **前端**：`frontend-vue/src/api/index.ts` 类型扩展、`InventoryView.vue` / `BatchesView.vue` 展示与筛选，调用现有接口。
- **测试**：更新 `tests/test_inventory_service.py` 既有断言，新增 `tests/test_batch_expiry.py`（扣减顺序 + 状态计算 + 查询契约）。
- **依赖 / 系统**：无新增依赖；纯后端逻辑 + 现有接口字段扩展 + 前端展示。
