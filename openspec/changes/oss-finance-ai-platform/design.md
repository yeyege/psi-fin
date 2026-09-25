## Context

See [proposal.md](proposal.md) for motivation. 关键约束与现状：

- 现有技术栈：FastAPI + SQLAlchemy 2.0 + Pydantic v2 / Vue 3 + TS + Element Plus + ECharts / MySQL(生产) + SQLite(开发)，Docker Compose + GitHub Actions，全部保留不引入新语言
- 已有业财半成品：`routers/finance.py`、`services/finance_service.py` 覆盖应收、收款核销、账龄；核销逻辑成熟但产生的是业务流水不是会计分录
- 单人开发、业余时间推进：每月有效编码时间有限，必须以 Phase 为发布单元控制范围
- 项目同时承担求职作品集职责：每个 Phase 结束时必须有「可演示的一句话 Demo」

## Goals / Non-Goals

**Goals:**
- 建立凭证内核：科目 → 凭证 → 总账 → 报表的最小完整闭环
- 凭证引擎完全规则表驱动，新增业务事件不改动引擎代码
- 财务数据不可变、可追溯：追加式凭证 + 红字冲销 + 期间锁账
- AI 以适配器方式接入，私有化部署可切 Ollama；所有 AI 写操作强制人工确认
- 开源门面完备：License、架构文档、seed 数据、CI 徽章、演示站，新人 `docker compose up` 一分钟内可看到完整演示

**Non-Goals:**
- **不做**税务申报、发票认证、金税对接等合规能力（定位管理会计/内部核算，README 显式声明）
- **不做**生产制造、多币种、合并报表、预算
- **不做**微服务拆分（模块化单体，模块间 service 层调用，禁止跨模块直接改表）
- **不做**AI 自动过账——任何 AI 产出必须经「草稿 → 人工确认 → 生效」
- **暂不做**多租户 SaaS 化（单租户实例先行，字段预留 tenant_id）

## Decisions

### D1: 演进路径 —— 本仓升级 vs 新仓库

**决策：本仓（wms-test）原地升级，Phase 0 完成 Monorepo 门面重组后改名发布。**

- 理由：保留 112 个后端测试、CI、Pages 演示站等全部工程资产；「从 WMS 长出财务」本身就是最好的演进故事
- 备选：新建仓库重开 → 丢掉测试与提交历史积累，放弃

### D2: 凭证引擎 —— 规则表驱动 vs 代码硬编码

**决策：三张配置表 + 一个引擎服务。**

```
posting_rule(id, event_type, enabled, memo)           -- 如 SALE_SHIPPED
posting_rule_line(id, rule_id, seq,
                  account_code_expr,                  -- 科目：常量或维度映射，如 AR 客户科目
                  direction,                          -- D/C
                  amount_source,                      -- 金额取值路径：货物金额/税额/含税总额
                  dimension_map)                      -- 辅助核算映射（客户/供应商/仓库）
account_mapping(id, event_type, dimension, account_code)  -- 维度值 → 科目 的映射表
```

引擎入口 `generate_voucher(db, event_type, doc)`：读规则 → 解析模板 → 组装分录 → 借贷平衡校验 → 落凭证，**与业务单据确认在同一事务内提交**；幂等键 `(event_type, doc_type, doc_id)`，重复事件直接返回已生成凭证。
- 理由：规则可被管理员在前端配置，是「业财一体」产品的灵魂设计，也是面试深挖点
- 备选：事件处理器写死 Python 代码 → 扩展性差、无配置界面卖点，放弃

### D3: 凭证不可变性

**决策：凭证状态机 `draft → posted → reversed`；posted 后禁止 UPDATE/DELETE 分录，更正一律生成红字（负额）冲销凭证并关联原凭证号；期间 `closed` 后引擎拒写该期间凭证（返回 409）。**

- 理由：审计要求 + 报表可追溯；实现上比"可改凭证"反而简单

### D4: 期间与结转

**决策：自然月期间（`period` 表），期末结转损益用一条内置规则 `PERIOD_CLOSE` 生成转账凭证（收入/费用类科目 → 本年利润），结转后锁定期间。** 反结账功能 v1 提供但仅管理员、留审计日志。

### D5: 成本核算

**决策：存货科目移动加权平均，出库成本在出库确认事件由凭证引擎按 `cost_amount` 取值（库存流水已有成本批次）；不在库存模块预先算好"财务成本"，避免两套口径。** 与批次成本（FIFO/效期，p0-2 已有）的口径差异写入 docs 架构文档。

### D6: AI 平台层 —— 适配与安全边界

**决策：**
- `app/ai/` 内置 `LlmClient` 适配层：统一 OpenAI 兼容协议（base_url + api_key 配置即切换 DeepSeek/Kimi/Ollama），不引入重框架（不用 LangChain，直接 httpx + pydantic 解析）
- 通用「AI 草稿」模式：所有 AI 场景产出先写 `ai_draft` 表（payload + 置信度 + 生成依据），前端确认页渲染成**可编辑的表单**，用户点确认后由对应业务 service 正式落库——AI 无数据库写权限，只读 + 产出草稿
- 全部 AI 调用记录 `ai_audit_log`（输入摘要、模型、耗时、token 成本）

### D7: ChatBI 语义层

**决策：不做裸 text-to-sql。** 预定义只读语义视图（如 `bi_v_sales_profit`、`bi_v_ar_aging`、`bi_v_inventory`），LLM 的任务是：选视图 + 生成受约束的查询参数（过滤/分组/聚合/排序/limit），后端用参数化 SQL 模板执行；无匹配视图时明确拒答并提示可用主题。
- 理由：可控、可测（mock LLM 即可跑单测）、防注入，符合私有化部署用户的安全预期

### D8: License

**决策：Apache-2.0。** 求传播优先，README 声明后续可能对「多租户 SaaS 托管版」保留商业双许可权利。
- 备选：AGPL-3.0 → 社区接受度与二次集成顾虑大，对个人项目传播不利，放弃

### D9: 「企业级」的定义 —— 工程纪律而非框架

**决策：技术栈不变（FastAPI + SQLAlchemy 2.0 + Pydantic v2 + MySQL 8）。**

- 认知纠偏：SQLAlchemy 2.0 是 Python 生态事实标准 ORM，「企业级」的成色由 D10-D13 的工程纪律决定，不由 ORM 决定；仓库现状已证明这套栈能支撑行级锁、状态机、126 用例等复杂约束
- 备选：换 Java/Spring Boot + MyBatis-Plus → 国内传统企服确实以 Java 为主，但推平现有全部资产与求职时间线不成比例；本项目以「Python + AI 原生 + 可私有化」差异化定位。若目标公司清一色 Java 栈，属求职策略问题而非本项目技术问题，另行评估

### D10: 金额精度口径 —— 财务域禁用 Float

**决策：会计域（account/voucher/voucher_line）全部金额字段用 `Numeric(18,2)` + Python `Decimal`，服务层计算用 Decimal 量化，借贷平衡比较不再用浮点容差 EPS。**

- 现状冲突：存量 `FinanceEntry` 等业务表为 Float + round(2)（历史「演示口径」）——业务域暂不改动以免破坏存量 112 用例；2.4 凭证引擎接入时应收/应付金额以 Decimal 边界转换，两套口径的转换点写入 docs
- 备选：整数存分（cents）→ 跨币种/税率乘除麻烦，Numeric 在 MySQL 即 DECIMAL，放弃
- **2026-09-26 修正（范围已扩大，本条取代上面的「暂不改动」）**：业务域一并迁移，不再保留两套口径。
  理由是「以免破坏存量 112 用例」这个顾虑已被实测证伪 —— 全量迁移后 130 用例全绿，未出现预期的大面积适配。
  两套口径共存的代价比预期高：`Decimal` 与 `float` 混算不是精度问题而是 `TypeError`，只要应收/应付仍是 Float，
  任何跨域汇总（驾驶舱、账龄、未来的凭证生成）都要在边界手工转换，转换点本身就是 bug 温床。
  落地：7 个金额列走 `models.base.Money`（`Numeric(18,2)`），量化入口 `app/common/money.py::money()`
  统一 `ROUND_HALF_UP`（取代 `round()` 的银行家舍入，属有意的业务口径变更），EPS 与两处 `1e-9` 容差删除；
  存量库由迁移 `0002_money_numeric` 转换，`backend-python/scripts/check_money_columns.py` 负责向数据库本身核对列类型；
  对外契约不变（`jsonable_encoder` 仍把 Decimal 输出为 JSON number），已用真实 HTTP 链路实测。

### D11: 迁移策略 —— Alembic 接线，废除裸 create_all

**决策：pyproject 已声明 alembic 但零使用，本 Phase 补齐：**
1. `alembic init` + 生成基线 migration（覆盖全部存量表）
2. 启动流程改跑 `alembic upgrade head`（Docker Compose backend entrypoint / 本地脚本），`Base.metadata.create_all` 仅保留给 pytest 临时库与开发便利
3. autogenerate 与模型一致性纳入 CI：`alembic check` 漂移即红

- **2026-09-26 进度（部分完成，勿整体视为已交付）**：
  - ①已完成：`alembic.ini` + `migrations/env.py`（只认 `DATABASE_URL`，缺失即退出，不静默回退 SQLite）；
    基线 `0001_baseline` 用 `Base.metadata.create_all(bind=op.get_bind())` 实现「覆盖全部存量表」，
    对存量库天然 no-op，因此不需要 `alembic stamp`；另加 `0002_money_numeric`（见 D10）。
    `alembic check` 在 SQLite 上实跑为「No new upgrade operations detected」，即模型与迁移零漂移。
  - ②未完成：`main.py` 的 lifespan 仍在启动时 `create_all`，compose 的 backend entrypoint 也没接
    `alembic upgrade head` —— 目前迁移由操作者显式执行。保留 lifespan 建表是为了不重写测试与
    全新环境冷启动路径，与「废除裸 create_all」尚有距离，收口时需要决定：是彻底移除 lifespan 建表
    （则新库必须先 upgrade），还是保留但明确它只建空表、不承担 ALTER（当前 AGENTS.md §4 采用后一种口径）。
  - ③未完成：`alembic check` 未进 CI。CI 目前只新增了一个 PostgreSQL 上的迁移可跑性 job
    （`backend-migrate-postgres`：空库 upgrade → 核对列类型 → downgrade → 再 upgrade），不等同于漂移检测。
- 注意：D10 修正后新增的列类型迁移证明了一件事 —— 只改模型不写迁移时，`create_all` 对已存在的表是 no-op，
  「测试库对了」与「线上库对了」是两个独立结论，必须分别取证

### D12: 数据库连接与引擎配置

**决策：`create_engine` 固定生产参数 + 补齐环境加载：**
- `pool_pre_ping=True`、`pool_recycle=3600`（断链防护，PG/MySQL 通用）、`pool_size=10, max_overflow=20`（SQLite 分支不适用）
- 事务隔离级别统一 `READ COMMITTED`（PG 默认即 RC，见 D17），会计汇总读取不依赖 RR 幻读语义
- `python-dotenv`（已在依赖未使用）：database.py 启动时 `load_dotenv()`
- **CI 增加真实数据库轨**：全量用例在 `DATABASE_URL` 指向生产同构库下再跑一遍；行级锁/并发防重入账类专测标 `@pg_only`（SQLite 下无 FOR UPDATE 语义，跳过）——否则「并发安全」在 CI 里从未被真实验证。具体轨道随 D17 定为 PG 主流 + MySQL 兼容夜间轨

### D13: 长耗时 AI 调用的执行模型 —— 不引入任务队列

**决策：v1 不加 Celery/Redis（运维负担与单人项目不匹配）。** AI 端点一律 `async def` + `httpx.AsyncClient`（带超时/重试）：ChatBI 用 SSE 流式返回缓解感知延迟；票据解析接受 30s 级同步请求（uvicorn 多 worker + 前端 pending 态）；Phase 4 批处理类（审计 Agent 全月扫描）再评估 arq+Redis 并单开 change
- 与栈的一致性说明：`aiosqlite`/`pytest-asyncio` 为历史残留，本项目 service 层保持**同步 SQLAlchemy**，异步仅用于 AI 出站 HTTP 调用，不混用两套 session

### D14: 凭证编号口径

**决策：记账凭证实行「按会计期间连续编号」：`JV-{yyyyMM}-{seq}`（新增 `generate_voucher_no(db, period_code)`），区别于业务单据的按日序列；已关闭期间的号段永久封存不得补号（断号容忍，错序不容忍）。** 业务单据号规则不变。

### D15: 目录结构 —— 撤销物理 Monorepo 重组

**决策：Phase 0 不做 `apps/` 物理迁移**（原 1.2），保留 `backend-python/`、`frontend-vue/` 目录现状，避免 Dockerfile/CI/e2e/Pages 全链路改路径的纯消耗；门面通过根 README、`docs/`、`examples/` 提供，物理重组推迟至 v1.0 后视社区反馈另开 change

### D16: Web 框架 —— 维持 FastAPI，不切 Django

**决策：不迁移 Django。** Django 无疑是企业级框架（Instagram/Spotify 背书），且若「今天从零开仓」，Django+Admin 在 auth/RBAC/迁移/后台 CRUD 上确实赢第一周——但在本项目现实下换栈不成立：

- 前端已是分离式 Vue3 SPA（BI 工作台已建成），Django 模板/Admin 优势被作废一半；DRF 样板量重于 FastAPI+Pydantic
- 126 存量用例与 service 层状态机重写约 3-4 周，且换框架不新增任何卖点——项目稀缺性在凭证引擎/会计内核/AI 人机协同，与 web 框架无关
- AI 场景（SSE 流式、httpx 异步出站）是 FastAPI 主场；Django 5.x 异步可用但 DRF 生态仍偏同步
-  SQLAlchemy 2.0 独立于 web 框架，若未来真需 Django 也只换接入层——此风险不存在

**重新评估触发条件**：产品形态退回「服务端渲染、无独立前端」时。

### D17: 主数据库 —— 切 PostgreSQL 16，MySQL 降级为兼容选项

**决策：生产/演示主库 PostgreSQL 16；MySQL 8.0 保留为兼容部署选项（compose profile + 每周 nightly CI 轨）；开发/测试 SQLite 不变。**

这不是赶时髦，是 D11/D12 工程纪律倒逼的结果：

| 理由 | 说明 |
|---|---|
| Alembic 可靠性 | PG 支持事务性 DDL，迁移失败可整体回滚；MySQL autogenerate 受 tinyint/charset 漂移噪音干扰，「alembic check 进 CI」在 MySQL 上会沦为狼来了 |
| 隔离级别 | PG 默认即 READ COMMITTED，与会计汇总读取口径天然一致（MySQL 默认 RR 需显式改） |
| 并发语义 | `SELECT ... FOR UPDATE / SKIP LOCKED` 行为完整可预测，是凭证幂等/防重入账真实验证轨的理想环境 |
| 开源先例 | Odoo/Metabase/n8n 等「可自托管企业开源软件」的默认面孔，与产品定位同构 |
| AI 协同预留 | pgvector：Phase 4 审计 Agent 的相似凭证比对/语义检索零新增组件 |

**迁移成本（现在切换恰为最低）**：SQLAlchemy 方言抹平差异，实际改动 = compose `mysql:8.0→postgres:16`、驱动 `pymysql→psycopg[binary]`、`.env.example` 与 CI 轨调整；业务代码零改动，越晚切越贵。
- 面试叙事：国内企业 MySQL 为主流，「一套 ORM 代码双库可移植」比死守单库更能证明工程能力；MySQL 兼容轨保留即为此服务
- 被否方案：维持 MySQL 主库 → D11 迁移体系长期不可靠；双主库同优先级 → CI 三倍轨维护成本，仅 PG 主流 + MySQL nightly 性价比最优

## Milestones（发布单元）

| Phase | 内容 | 一句话演示 | 预估 |
|---|---|---|---|
| 0 | 开源门面：License/文档/seed/CI 徽章 | `docker compose up` 出完整 WMS 演示 | 1 周 |
| 1 | 财务内核 + 凭证引擎 + 两张报表 | **点「发货」→ 凭证自动生成 → 利润表数字变化** | 3-4 周 |
| 2 | 采购/应付/费用 + 移动加权成本 + 结转锁账 | 采购到付款全链路进报表 | 3 周 |
| 3 | AI 平台层 + ChatBI + 票据入账 | 问「上月华东仓毛利排名」出图表；传发票出草稿凭证 | 3 周 |
| 4 | 异常审计 Agent + 运营迭代 | 月末一键体检报告 | 持续 |

## Risks / Trade-offs

- **[范围失控] ERP 是无底洞** → 以 Non-Goals 清单为硬边界；每 Phase 有明确发布演示，做不完就砍进下个 Phase，不阻塞发布
- **[会计正确性] 单人项目报表算错会砸口碑** → 借贷平衡/试算平衡作为强制不变量入测试；发布前用一套手工编制的标准案例（10 笔典型业务）对两张报表做人工核对，核对表随 demo 数据发布
- **[合规边界] 财税合规风险** → 产品定位「管理会计/内部核算」，README/文档显式声明非报账报税用途
- **[LLM 依赖] 外部模型不可用/成本** → 适配层保证 Ollama 本地兜底；ChatBI/OCR 均设计为「可关闭」的可选模块，核心 ERP 不依赖 AI 可独立运行
- **[单人节奏] 中断风险** → 全部走 openspec + 测试先行，任何时刻可交接/暂停/恢复

## Open Questions

- 前端是否随 Phase 0 一并重排菜单信息架构（财务一级菜单）？倾向：是，改 `router` 与侧边栏即可
- seed 演示数据的时间跨度与量级（建议：近 6 个月、约 50 客户 / 200 SKU / 3000 单据，seeded PRNG 可复现）
