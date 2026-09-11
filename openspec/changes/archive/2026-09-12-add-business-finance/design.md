## Context

见 proposal.md - Why。现状要点(已核对代码):

- `backend-python`:FastAPI + SQLAlchemy,`Base.metadata.create_all` 建表(默认 SQLite `wms.db`,可切 MySQL),已有 商品/客户/仓库/库位/批次/库存/库存流水/出入库/波次/退货/移库/盘点/看板/鉴权 等域;响应统一为 `{code, data, message}`,分页统一为 `{list, total, page, pageSize}`;`docker-compose.yml` 已内建 MySQL 8 服务与 `DATABASE_URL` 注入。
- `Customer` 表**没有**账期/信用额度字段;`Batch` 表**没有**成本价字段;`OutboundOrder` 不挂金额与商品单价。
- `frontend-vue`:Vue3 + Element Plus + ECharts 6 + vue-router(hash)+ pinia;`api/index.ts` 集中声明接口与类型;`App.vue` 承载侧边导航。
- 结论:业财层所需的字段(金额、账期、单价)在既有表中都不存在,硬改老表要面对 SQLite 无迁移工具的问题,因此**全部落在新增表**上。

## Goals / Non-Goals

**Goals:**

- 打通收入侧业财闭环:销售订单(确认 → 发货)→ 发货自动生成应收 → 收款核销(含部分核销与预收)→ 应收余额/账龄/驾驶舱。
- 业财口径单一:所有金额只有一个来源(业务单据 + 财务流水),驾驶舱不另算一套。
- 纯增量落地:不修改既有表结构、不改变既有页面与接口行为。
- 系统定位从 WMS 升维为「进销存 + 业财一体中后台」。

**Non-Goals:**

- 不做"订单驱动库存出库":发货是**业务状态动作**,不自动创建出库单、不扣减库存,库存仍走既有出库流程(关联出库单号一期只预留字段,允许为空)。
- 不做成本与毛利核算——现有批次无成本字段,需要时另立变更(涉及老表加列 + 数据迁移方案)。
- 不做采购应付落库——`InboundOrder.supplier_name` 是文本,供应商未建表;成本侧(采购 → 应付 → 付款)留后续变更。
- 不引入新角色权限模型——沿用现有 `admin/operator`,财务页面对已登录用户开放,权限细化留后续。

## Decisions

### 1. 载体:扩展现有仓库并重定位(备选:新建独立项目)

库存底座(批次/库存/流水)已完整且业财的成本数据本就来自库存;新建项目要重写登录、路由、UI 框架与库存流程,收益仅是仓库命名更纯粹。因此选择扩展 + 通过导航与 README 完成定位升维,WMS 归入"库存"板块。

### 2. 数据模型:4 张新表,零老表改动

- `sales_orders`:id、order_no(唯一)、customer_id、customer_name(冗余便于查询)、status(DRAFT/CONFIRMED/SHIPPED/COMPLETED/CANCELLED)、credit_days(账期天数)、total_amount、**outbound_order_no(可空,预留关联出库单)**、**shipped_at(可空,发货时间)**、remark、created_at、updated_at
- `sales_order_items`:id、order_id、product_id、product_name、quantity、unit_price、amount
- `finance_entries`:id、entry_no(唯一)、entry_type(RECEIVABLE/PAYABLE/RECEIPT/PAYMENT)、partner_type(CUSTOMER/SUPPLIER)、partner_id、partner_name、source_order_no、amount、settled_amount(已核销,默认 0)、occurred_date、due_date、status(OPEN/PARTIAL/SETTLED)、remark、created_at;**唯一约束 (source_order_no, entry_type)**
- `finance_settlements`:id、receipt_entry_id(收款/付款流水)、target_entry_id(应收/应付流水)、amount、created_at

理由:账期/单价/金额这些既有表没有的字段全部落在新表;`outbound_order_no` / `shipped_at` **现在就预留**——新增表以后再加列同样要迁移,现在建好零成本,后续打通"订单→发货"不用改表。备选:给 `Customer`/`Batch` 加列 → 需处理 SQLite 迁移,一期不做。

### 3. 核销模型:流水 + 核销明细(支持部分核销与预收)

应收金额与已核销金额分离,核销动作写 `finance_settlements` 一行并累加目标流水的 `settled_amount`;应收状态由"已核销 vs 金额"推导(0=OPEN、小于=PARTIAL、等于=SETTLED)。
**预收**:收款流水的 `amount` 是实际到账金额,`settled_amount` 是已核销金额,二者之差即该笔收款的未核销余额(预收),可再次核销到其他应收——因此"收款金额 > 已核销金额"是合法状态,只有"对单张应收的核销额 > 该应收未结余额"才拒绝。
备选:收款流水直接覆盖应收状态(不支持部分核销、无法追溯多笔核销) → 放弃。

### 4. 应收生成时机与幂等

应收在**发货动作**内、同一事务中生成;到期日 = 发货日期 + 账期。
幂等采用**三层防护**:① DB 唯一约束 `(source_order_no, entry_type)` 兜底;② 服务层生成前先查是否已存在,存在则直接返回既有记录;③ 捕获 `IntegrityError` 时按幂等处理(不报错、不产生第二条)。
理由:并发下仅靠"状态机判断"不可靠(两个请求可能同时通过状态检查),必须由数据库约束兜底。

### 5. 账龄实时计算,不落库

账龄**以到期日为基准**,按 `due_date` 与 `date.today()` 的比较实时分段(未到期 / 逾期1-30 / 31-60 / 60+),不新增存储字段,避免"数据过期"和口径漂移;所有账龄与余额计算集中在 `finance_service` 的单一函数内,供列表与驾驶舱复用。

### 6. 契约与前端沿用既有约定

- 后端:路由挂 `/api` 前缀,响应 `{code, data, message}`;列表分页 `{list, total, page, pageSize}`;沿用 `app/common/order_no.py` 生成单号(前缀 `SO` / `AR` / `RC`)与"唯一约束 + IntegrityError 重试"策略。
- 前端:新增 `SalesOrdersView`、`FinanceView`、`ExecutiveView`;接口与类型集中加在 `api/index.ts`;驾驶舱用 ECharts(项目已依赖 echarts 6);导航按业务域分组。

## Risks / Trade-offs

- [老表无成本字段 → 无法算毛利] → 一期明确不做成本/毛利,提案与文案不承诺;后续变更单独处理老表加列与数据迁移。
- [发货是人工状态动作,可能与库存实际发货不一致] → 一期由业务人工确认发货,不校验库存;后续打通出库单时再补一致性校验(关联出库单号字段已预留)。
- [订单确认后明细仍可改 → 应收金额与实际不符] → 仅 DRAFT 允许编辑明细,确认后明细只读。
- [账龄/余额口径在多处重复实现导致不一致] → 统一收敛到 `finance_service` 单一函数,并用测试固定口径。
- [SQLite 并发下单号/应收唯一冲突] → 唯一约束 + 服务层幂等 + IntegrityError 捕获,三层防护。
- [日期比较口径混乱(时间戳 vs 日期)] → 到期日与账龄统一按日期(取 date)比较,规避时分秒误差。
- [重定位动导航可能漏掉老入口] → 定位任务里显式包含"原有 15 个页面逐一点检可达"的验证。

## Migration Plan

- 部署:启动时 `create_all` 自动创建 4 张新表,无需手工迁移;老表与老数据不动。
- 回滚:回退代码即可;如需彻底清理,删除 4 张新表,不影响任何既有功能与数据。
- 实施顺序:模型/建表 → 销售订单服务(含发货)→ 应收核销服务 → 路由注册 → 后端测试 → 前端接口 → 前端页面 → 重定位(导航/标题/README)→ 联调验证。
