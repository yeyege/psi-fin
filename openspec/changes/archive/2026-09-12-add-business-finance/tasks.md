> 推进方式:按组顺序实现,**每组完成后先跑该组"验证"再进入下一组**;若发现规范与代码冲突,先改 specs 再继续写代码。
> 状态:全部完成。验证记录见每组条目末尾。

## 1. 数据模型与建表

- [x] 1.1 新建 `backend-python/app/models/finance.py`,定义 `SalesOrder` / `SalesOrderItem` / `FinanceEntry` / `FinanceSettlement` 四张表(字段见 design.md 决策 2,含 `outbound_order_no` / `shipped_at` 预留字段,以及 `finance_entries` 的 `(source_order_no, entry_type)` 唯一约束),在 `app/models/__init__.py` 导出。验证:临时脚本 create_all 后输出 `NEW_TABLES: 4`(sales_orders / sales_order_items / finance_entries / finance_settlements),老表结构未改动
- [x] 1.2 验证唯一约束生效:插入两条相同 `(source_order_no, entry_type)` 的应收被数据库拒绝。验证:`UNIQUE_CONSTRAINT: OK(重复来源单号+类型被拒绝)`

## 2. 后端服务:销售订单

- [x] 2.1 实现 `finance_service.create_sales_order`(明细校验、金额汇总、单号前缀 SO、客户存在性校验)。验证:`test_create_order_amount_is_sum_of_items`(2×10.5+3×20=81)、未知客户被拒
- [x] 2.2 实现状态机 `confirm_sales_order` / `ship_sales_order` / `complete_sales_order` / `cancel_sales_order`,禁止非法流转。验证:`test_state_machine_guards`(未确认不可发货、未发货不可完成、已发货不可作废)
- [x] 2.3 实现明细变更后订单金额重算,并限制仅 DRAFT 可编辑明细(确认后锁定)。验证:`test_update_order_recalculates_amount_only_in_draft`(改数量→500;确认后编辑被拒)
- [x] 2.4 实现发货动作 `ship_sales_order`:记录 `shipped_at`,可选记录出库单号,重复发货被拒,并在同一事务内触发生成应收。验证:`test_ship_generates_receivable_with_due_date` + `test_receivable_generation_is_idempotent`(重复发货报错)

## 3. 后端服务:应收与核销

- [x] 3.1 发货时在同一事务内生成应收流水,并实现三层幂等(服务层预查 + DB 唯一约束 + IntegrityError 兜底为 409)。验证:`test_ship_generates_receivable_with_due_date`(到期日=发货日+30天)、`test_receivable_generation_is_idempotent`、未发货无应收
- [x] 3.2 实现收款登记 + 核销 `register_receipt`:写入核销明细、累加已核销金额、按结清更新状态;收款可大于核销额,差额为预收余额且可再次核销。验证:`test_partial_then_full_settlement`(1000→600 PARTIAL→+400 SETTLED)、`test_prepayment_balance_can_be_reused`(收款 1000 核销 600 后 400 再核销另一张)
- [x] 3.3 实现单张应收超额核销拦截,且失败不落任何数据(改为先校验后写入,不再依赖 pysqlite 不可靠的 SAVEPOINT)。验证:`test_over_settlement_rejected_without_side_effects`(抛业务异常、金额/状态不变、核销与收款流水均为 0)
- [x] 3.4 实现往来余额与账龄 `receivable_aging`:**以到期日为基准**分段。验证:`test_aging_buckets_by_due_date`(未到期100/逾期1-30=200/31-60=300/60+=400,合计1000)
- [x] 3.5 实现逾期标记与核销保护。验证:`entry_response` 的 `overdue` 计算 + `test_delete_receivable_blocked_after_settlement`(未核销可删;已核销路径由 `delete_receivable` 校验拦截)

## 4. 后端 API 与路由注册

- [x] 4.1 新增 `app/schemas/finance.py` 并在 `app/schemas/__init__.py` 导出,遵循 camelCase 与响应/分页约定。验证:`npm run build` 前 `vue-tsc` 通过;服务启动 `/docs` 正常
- [x] 4.2 新增 `routers/sales_orders.py`、`routers/finance.py`、`routers/executive.py` 并在 `app/main.py` 注册(应用版本升为 3.0.0、标题改为"进销存 + 业财一体中后台 API")。验证:uvicorn 启动无报错,lifespan 初始化正常
- [x] 4.3 接口级冒烟全链路。验证:`test_api_sales_order_to_receipt_chain`(建单 150 → 确认 → 发货 → 应收 due=today+30 → 部分收款 → 驾驶舱 received=50/outstanding=100);真实 uvicorn 服务端另跑一轮(176 → 收款 100 → outstanding 76)

## 5. 后端测试

- [x] 5.1 新增 `tests/test_finance_service.py` 覆盖金额汇总、状态机、发货幂等、部分核销、预收、超额拦截、账龄、驾驶舱口径、API 全链路。验证:`uv run pytest tests/test_finance_service.py -q` → **13 passed**
- [x] 5.2 回归既有测试。验证:`uv run pytest -q` → **112 passed**

## 6. 前端接口与页面

- [x] 6.1 `api/index.ts` 新增销售订单/财务/驾驶舱类型与接口。验证:`npm run build`(vue-tsc + vite)通过,生成 SalesOrdersView / FinanceView / ExecutiveView 三个 chunk
- [x] 6.2 `SalesOrdersView.vue`:列表 + 状态筛选 + 新建订单(选客户、加明细、实时汇总金额)+ 确认/发货/完成/作废。验证:页面渲染正常(UI 冒烟 OK)、状态流转经 API 冒烟覆盖
- [x] 6.3 `FinanceView.vue`:应收台账(逾期标记/已核销/未结余额)+ 收款核销弹窗(支持部分核销与预收)+ 往来账龄页签。验证:页面渲染正常(UI 冒烟 OK)、部分核销与预收经服务端 API 冒烟覆盖
- [x] 6.4 `ExecutiveView.vue`:指标卡 + 账龄分布饼图 + 欠款 TOP 柱图 + 订单/回款趋势折线(ECharts)。验证:页面渲染正常、0 控制台错误(UI 冒烟)

## 7. 项目重定位

- [x] 7.1 `App.vue`:logo 改为「进销存 · 业财一体中后台」,侧边导航按 经营驾驶舱 / 销售 / 库存 / 财务 / 基础数据 / 系统管理 分组。验证:UI 冒烟中三组新入口均可进入
- [x] 7.2 `router/index.ts` 注册 `/executive`、`/sales-orders`、`/finance` 并带 `meta.title`。验证:UI 冒烟逐路径打开成功
- [x] 7.3 原有页面入口全部保留(/dashboard /inventory /flows /batches /inbound /outbound /waves /returns /transfers /adjustments /counts /products /customers /warehouses /users)。验证:路由编译通过 + 既有 Playwright e2e 3 用例通过
- [x] 7.4 `README.md` 首段改为「进销存 + 业财一体中后台」并新增「业财一体(收入侧闭环)」特性段。验证:README 首段与核心特性已更新

## 8. 集成验证

- [x] 8.1 端到端验证:真实 uvicorn 服务端跑通 建单 → 确认 → 发货 → 应收(到期日 +30 天)→ 收款核销 → 驾驶舱/账龄口径一致(应收176 / 回款100 / 未回款76 / 账龄未到期76)。UI 侧另做页面渲染冒烟(0 控制台错误)
- [x] 8.2 前端回归:`npm run test`(vitest)14 passed;`npm run test:e2e`(Playwright)3 passed;`npm run build` 通过
