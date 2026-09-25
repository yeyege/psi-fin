# 业务术语表

本项目的**规定性**词表：写文档、提问、命名测试、起变量名时优先用这里的词，第一次出现就在
上下文里解释清楚。它取代 `.qoder/repowiki/` 里的自动产物（该目录是 IDE 重建物，已决定不入库，
见 `.gitignore`）——自动产物会随重建漂移，不能作为 `AGENTS.md` §5「测试名读起来像规格」的依据。

摘出与重写时间：2026-09-26。新增条目来自本仓库已落地的代码事实，不是设想。

---

### 进销存 · 业财一体中后台系统
- 定义：本项目官方定位。以 WMS（入库/出库/波次拣货/退货/移库调拨/盘点/批次）为业务底座，叠加销售订单与财务应收，打通「销售订单 → 发货自动生成应收 → 收款核销（含部分核销/预收）→ 应收余额与账龄 → 经营驾驶舱」的收入侧闭环。属于轻量级 ERP，不是全栈 ERP。
- 别名：业财一体化中后台、收入侧业财闭环

### 经营驾驶舱
- 定义：基于业务库**同源数据**构建的内嵌 BI 看板，展示应收总额、已回款/未回款、逾期、欠款 TOP、账龄分布、出入库分析、作业效率、经营财务趋势。区别于外挂 ETL 的独立 BI 系统：数字必须能追溯到业务表，不接受另建一份数据。
- 别名：BI 驾驶舱、`BiWorkbenchView`

### 会计内核
- 定义：自研管理会计模块，含科目表（COA）、记账凭证、会计期间。能力边界：借贷平衡强校验、过账后不可改、红字冲销双向留痕、期间结账后锁定。定位为**内部核算**而非报税合规财务软件。
- 别名：凭证引擎、总账内核

### 可用量 / 锁定量分离
- 定义：库存模型把 `available_qty`（可被新订单占用）与 `locked_qty`（已被出库单承诺但未发货）分成两列，隔离「已承诺未出库」部分，是防超卖的前提。
- 别名：库存双量模型

### 波次拣货
- 定义：将多个出库单聚合成一个波次，按库位优先级排序生成拣货单；拣货时先锁定库存再发货，是出库流程的前置环节。
- 别名：wave picking、`WavesView`

### 防超卖
- 定义：并发安全机制集合：行级 `SELECT ... FOR UPDATE` + 条件 UPDATE（`WHERE available_qty >= take`）+ 失败重读重试；任一明细失败则**整单 rollback**。
- **方言事实（勿再写错）**：`FOR UPDATE` 在 SQLite 被**静默忽略**，在 **MySQL 8.0 与 PostgreSQL 均生效**。因此单测（SQLite）跑绿不构成并发正确性的证据。
- 别名：并发扣减、原子扣减

### 方言三态
- 定义：同一套 ORM 代码在本项目跑在三种方言上，行为并不等价，任何结论都必须写明观察来自哪一态：
  ① 单测（`tests/conftest.py` 临时 SQLite）；② 本地开发（不设 `DATABASE_URL` 时默认 SQLite `psi_fin.db`，
  `npm start` 即此态）；③ 持久库（compose 的 MySQL 8.0 / 线上演示的 Neon PostgreSQL）。
- 别名：三库并存、SQLite 陷阱

### 金额口径
- 定义：全部金额列为 `Numeric(18,2)`（列类型别名 `app.models.base.Money`），服务层只经
  `app/common/money.py::money()` 量化，舍入固定 `ROUND_HALF_UP`；比较一律用精确相等，
  **禁止 `EPS`/`1e-9` 容差兜浮点残差**。`Decimal` 与 `float` 混算是 `TypeError` 而非精度问题，
  所以 `func.sum` 等聚合结果也必须先过 `money()`。尺寸重量（`width/height/length/weight`）不是金额，保持 `Float`。
- 别名：Decimal 定点、四舍五入到分

### 迁移与建表的分工
- 定义：`Base.metadata.create_all` 只建**缺失的表**，不会 `ALTER` 已存在的列；持久库的列结构变更
  必须由 Alembic 迁移承载（`backend-python/migrations/versions/`）。测试库与全新环境冷启动走
  `create_all`。「改了模型没写迁移」= 新库和测试库对了、线上与本地存量库仍是旧类型。
- 别名：Alembic 门禁、create_all 局限

### Seam（缝隙 / 接缝）
- 定义：观察行为而不伸手进实现的公共边界。本项目的 seam 是 service 层入口
  （`inventory_service.add_stock` / `deduct_stock` 等）与 HTTP 响应契约；测试打在 seam 上，不打在内部实现上。
- 用法约束：见 `AGENTS.md` §5。新增公共 seam 需先确认；对既有 seam 补测试与回归测试无需确认。

### CamelModel 契约
- 定义：前后端统一 camelCase 字段命名的 Pydantic 基类，输入输出同时兼容，避免两侧字段名不一致。
- 别名：camelCase 契约

### 统一响应信封
- 定义：所有接口返回 `{code, message, data}`。创建类 201，查询/动作类 200；列表返回
  `{list, total, page, pageSize}`，按 `created_at desc, id desc` 排序；业务异常统一
  `raise BusinessError(...)` 由全局处理器转 JSON。
- 别名：响应信封、`{code,message,data}`

### MVP 里程碑（M1-M7）
- 定义：分阶段交付编号：M1 客户管理、M2 商品扩展（FNSKU/箱规）、M3 数据看板、M4 退货管理、
  M5 波次拣货、M6 复核验货、M7 用户权限（admin/operator 双角色、PBKDF2-SHA256 密码哈希、Token 鉴权）。
- 别名：M1-M7

---

## 维护约定

- 新增术语的门槛：**这个词汇别的名字会让人误解代码**，或者它标记了一处会反复踩的坑。
  单纯起个变量名不算。
- 本表与 `AGENTS.md` 冲突时以 `AGENTS.md` 为准；本表与 repowiki 自动产物冲突时以本表为准
  （后者是重建物，不入库）。
