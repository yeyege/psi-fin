## Context

See [proposal.md](proposal.md) — Why。当前实现现状：

- `deduct_stock` / `lock_stock` / `ship_stock` 三个入口共享同构的「先 SUM 校验 → 逐行取最前候选 → 条件 UPDATE + 失败重读重试」循环，唯一差别是取行条件（`available_qty > 0` / `locked_qty > 0`）与流水类型；三处的候选排序目前都是 `.order_by(Inventory.id.asc())`（≈建批先后，见 [inventory_service.py](file:///d:/wms-test/backend-python/app/services/inventory_service.py)）。
- `Batch` 已含 `inbound_date`（必填）、`manufacture_date`（可空）、`expiry_date`（可空），无需表结构变更；`Inventory.batch_id` 可空（无批次库存行存在于盘盈/调整等场景）。
- 调用方固定签名不变：出库/波次 `lock_stock`+`ship_stock`、移库/调整/盘点 `deduct_stock`，均以 `(product_id, location_code, quantity)` 聚合调用（见 outbound_service.py / wave_service.py / transfer_service.py / adjustment_service.py / count_service.py）。
- SQLite（开发）无 `NULLS LAST` 语义时靠 CASE 兜底；PostgreSQL 生产库同代码可跑。
- 前端批次页与库存库位明细页已存在；批次汇总卡片当前为 Mock 数据（[BatchesView.vue](file:///d:/wms-test/frontend-vue/src/views/BatchesView.vue) 中 `summaryCards`）。

## Goals / Non-Goals

**Goals:**
- 在不改函数签名、不引入表迁移的前提下，让全部跨批次扣减按「先到期先出」选择批次，且无批次行最后扣。
- 扣减排序规则抽成单一实现点，三个入口复用，避免漂移。
- 批次状态（正常/临期/已过期/呆滞）计算集中在后端一处纯函数，供明细与列表两处查询复用。
- 查询接口只增字段（+可选状态筛选参数），REST 路径与既有字段保持向后兼容。

**Non-Goals:**
- 不做库存行级到期自动冻结/锁定（如临期批次禁止新建出库单）——留待后续策略，本 change 只保证"先到期先出"+可视预警。
- 不做批次合并/效期修改等批次治理功能。
- 不迁移到 PostgreSQL（P0-4 范畴）；本 change 保持 SQLite 开发库可跑通即可。
- 不新增缓存（Redis 属 P2-9）。

## Decisions

### D1: 候选排序抽成共享 SQL 排序表达式

**决策：在 `inventory_service.py` 内新增共享 helper 生成排序条件，三个扣减函数统一使用。**

排序键（对候选 Inventory 行，outerjoin Batch 后）：
1. `batch 为空` 排最后（CASE 置 1，有批次置 0）；
2. 日期键 = `COALESCE(expiry_date, manufacture_date, inbound_date)` 升序 —— 即有效期最早到期优先，无有效期退回生产日期，再无退回入库日期；
3. 完全同日期时按 `Batch.id ASC, Inventory.id ASC` 稳定排序（保持既有"早期批次先扣"在无日期差异时的行为，使现有 FIFO 测试语义延续）。

- 理由：一条 SQL 排序满足 spec 的 4 级回退链，三入口共用保证 ship 与 lock 同序；CASE/COALESCE 兼容 SQLite 与 PostgreSQL。
- 备选 A：取行后 Python 排序 → 需要把候选全量拉出再挑，破坏逐行 `FOR UPDATE + 条件 UPDATE` 的并发原子设计，放弃。
- 备选 B：三处各自复制排序 → 违背单一实现点，易漂移，放弃。

### D2: 并发原子语义保持不变

**决策：保留现有「先 SUM 校验总量 → 循环取排序最前候选行 `with_for_update` → `WHERE available_qty >= take` 条件 UPDATE，rowcount=0 则重读重试」。**

排序改动只影响"候选行里先取哪行"，不影响不足即 False 无副作用的保证。循环每次重新执行排序查询，故并发下已扣尽的行自然被过滤，下一轮取到次优先候选，顺序不会错乱。

### D3: 批次状态计算集中在后端单一纯函数

**决策：在 service 层提供 `batch_lifecycle(batch, now)`（或等价纯函数）返回 `(status, days_to_expiry, age_days)`，`query_inventory`(location 视图) 与 `query_batches` 共用；阈值作为模块常量（临期 30 天 / 呆滞 180 天），不落库。**

- 理由：口径一致（spec 要求两处一致）、可单测。
- 备选：前端各自算 → 两份口径必然漂移，且列表分页服务端计算更正确，放弃。

### D4: 查询接口只增字段与可选参数

**决策：**
- `GET /api/inventory?view=location`：每行新增 `manufactureDate / expiryDate / daysToExpiry / ageDays / batchStatus`。
- `GET /api/inventory/batches?status=`：每行新增 `ageDays / batchStatus`；支持可选 `status` 过滤（normal | expiring | expired | aging），缺省不过滤。
- status 值映射用英文枚举（`NORMAL / EXPIRING / EXPIRED / AGING`）出参，展示文案由前端映射中文。

理由：符合既有 camelCase 契约（`CamelModel` 自动映射）；新增字段向后兼容。

### D5: 前端预警展示

**决策：** InventoryView（location 视图）与 BatchesView 增加"状态"列与 Element Plus Tag（临期 warning / 已过期 danger / 呆滞 warning-暗 / 正常 success），BatchesView 增加状态筛选下拉。Mock 汇总卡片本次保留（替换真实计数留作后续看板接口化，避免本 change 范围膨胀）。

## Risks / Trade-offs

- [排序 SQL 在 SQLite 下日期空值需 CASE/COALESCE 兜底，避免 `NULLS LAST` 兼容问题] → D1 用 COALESCE 折叠 + CASE 把无批次行置后，不依赖数据库方言 NULLS 语法。
- [ship 与 lock 若排序实现分开可能漂移] → 三入口共用同一排序 helper（D1），并由测试锁定"拣货与发货同序"。
- [排序从建批顺序改为效期顺序会改变既有扣减结果，部分既有 FIFO 单测断言可能受影响] → 无日期差别的批次因回退键 + `Batch.id` 稳定序仍保持"早期批次先扣"，仅显式构造日期差异的用例会变化；逐条核对既有 `test_deduct_stock_cross_batch_fifo`（helper 用 `datetime.now()`，两批次日期相同）仍应通过。
- [新增字段增大响应体] → 字段为轻量标量，列表分页 20 行/页，可忽略。
- [中文状态 vs 接口枚举] → 出参英文枚举 + 前端映射，避免后端依赖前端文案；口径测试覆盖枚举。

## Migration Plan

- 无数据迁移（不改表结构、不加列）。部署/回滚即替换 service/查询代码：回滚到上一 commit 即可恢复旧排序，无残留状态。
- 发布顺序建议：先合并后端排序 + 状态计算 + 单测，再合并前端展示；前端新字段对旧后端容错（缺省显示"-"）。

## Open Questions

无。临期/呆滞阈值（30/180 天）先以模块常量落地并在设计文档与 tasks 中标注可配置化留待后续，不阻塞本次实现。
