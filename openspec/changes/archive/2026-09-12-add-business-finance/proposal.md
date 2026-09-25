## Why

现有仓库 `wms-test` 是一套完整的**仓储执行层**系统(出入库、波次拣货、盘点、批次库存),但缺少「业财一体」最关键的一层:**业务单据 → 财务记录**。招聘方要的中后台是"进销存 + 业财一体",而当前项目定位只写到 WMS 这一层——库存底座已经具备,补上销售域与财务域即可形成完整闭环,成本远低于另起项目。同时项目名称与导航需要一次**重定位**,否则"用 WMS 讲业财"会显得名不符实。

## What Changes

- 新增**销售订单域**:销售订单主表 + 明细子表,支持 草稿 → 已确认 → 已完成 / 已作废 状态流转,金额由明细汇总。
- 新增**财务域**:统一财务流水(应收 / 应付 / 收款 / 付款),支持**自动生成应收**与**收付款核销**(含部分核销),并计算往来余额与账龄。
- 新增**经营驾驶舱**:应收余额 TOP 客户、账龄分布、订单金额与回款趋势(ECharts),数据来自真实业务单据。
- **项目重定位**:导航、标题、README 从「WMS 仓储管理」升维为「进销存 + 业财一体中后台」,WMS 相关页面归入"库存"板块。
- **一期范围(收入侧闭环)**:销售订单 → 应收自动生成 → 收款核销 → 驾驶舱。成本侧(采购入库 → 应付 → 付款)与"订单驱动库存出库 / 成本毛利"留到后续变更。
- **不动既有表结构与既有行为**:不修改 customers / products / batches / inbound_orders 等已有表(避免 SQLite 无迁移工具带来的风险),不改造现有出入库流程;新能力全部落在**新增表**上,由 `create_all` 自动建表。

## Capabilities

### New Capabilities
- `finance/sales-order`: 销售订单域 — 订单与明细的增删改查、金额汇总、状态机流转(草稿/已确认/已完成/已作废)、订单号生成与列表筛选。
- `finance/receivable`: 应收与核销 — 销售订单确认后自动生成应收流水;收款登记并按单核销(支持部分核销);按往来方计算应收余额、账龄分段与到期预警。
- `finance/executive-dashboard`: 经营驾驶舱 — 应收余额、账龄分布、订单金额趋势、回款趋势等聚合指标,供管理层查看。
- `platform/positioning`: 项目重定位 — 系统标题、导航分组与 README 从「WMS」升维为「进销存 + 业财一体中后台」,库存功能作为其中一个板块。

### Modified Capabilities
(无。现有 WMS 能力的行为规范不变。)

## Impact

- **后端**:新增 `app/models/finance.py`、`app/schemas/finance.py`、`app/services/finance_service.py`、`app/routers/sales_orders.py`、`app/routers/finance.py`、`app/routers/executive.py`,并在 `app/main.py` 注册路由与 `app/models/__init__.py` 导出;新增 `tests/test_finance_service.py`。
- **前端**:新增 `views/SalesOrdersView.vue`、`views/FinanceView.vue`、`views/ExecutiveView.vue`;扩展 `api/index.ts`、`router/index.ts`、`App.vue`(导航分组与标题)。
- **数据**:仅新增表(`sales_orders` / `sales_order_items` / `finance_entries` / `finance_settlements`),不修改既有表;SQLite 由 `Base.metadata.create_all` 自动创建。
- **文档/定位**:更新 `README.md` 定位描述;不改动 `openspec/` 既有已归档规范。
- **无新增依赖**:沿用 FastAPI + SQLAlchemy(SQLite/MySQL)+ Vue3 + Element Plus + ECharts。
- **兼容性**:现有 15 个前端页面、后端 API 与测试不受影响(纯增量)。
