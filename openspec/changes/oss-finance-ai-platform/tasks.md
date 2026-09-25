## 1. Phase 0 · 开源门面（1 周）

- [ ] 1.1 定版 Apache-2.0 LICENSE；README 重写（定位一句话、GIF 演示位、快速开始、Non-Goals 声明、徽章位：CI/覆盖率/License）；补 CONTRIBUTING.md 与 issue/PR 模板。验证：新机器按 README 步骤 10 分钟内跑起系统
- [ ] 1.2 目录门面（不物理重组，见 D15）：新增根 README/docs/examples/LICENSE，保留 backend-python、frontend-vue 现状。验证：CI/e2e/Docker 路径零修改且全绿
- [ ] 1.3 一键 seed 演示数据脚本（seeded PRNG 可复现）：近 6 个月、50 客户/200 SKU/约 3000 单据，覆盖全部业务状态。验证：连续两次 seed 产出数据摘要（各表 count + 关键金额合计）完全一致
- [ ] 1.4 docs 架构文档骨架：系统架构图（C4 Level 2）、领域模型图、模块依赖约定（禁止跨模块直改表）。验证：文档站内可访问
- [ ] 1.5 Alembic 接线（D11）：`alembic init` + 基线 migration 覆盖全部存量表；启动入口改 `alembic upgrade head`，create_all 仅限 pytest 临时库。验证：空库一键升级到 head；`alembic check` 无漂移
  - [x] 1.5a 工具链与基线：`alembic.ini` + `migrations/env.py`（只认 `DATABASE_URL`，缺失即退出）+ `0001_baseline`（create_all 实现，对存量库 no-op、无需 stamp）；空库 upgrade 到 head 已在 SQLite 实跑；`alembic check` 零漂移
  - [ ] 1.5b 启动入口接 `alembic upgrade head`（compose backend entrypoint / 本地脚本）；决定 `main.py` lifespan 的 create_all 是否彻底移除（见 D11 进度注）
  - [ ] 1.5c `alembic check` 进 CI，漂移即红（当前只有 PG 上的迁移可跑性 job，不等于漂移检测）
- [ ] 1.6 引擎与连接配置（D12/D17）：pool_pre_ping/pool_recycle/pool_size、load_dotenv 补齐；compose 主库切 `postgres:16`（MySQL 保留为 profile 兼容选项）、驱动加 psycopg[binary]、.env.example/README 同步。验证：PG 容器重启后首请求成功；alembic autogenerate 在 PG 上零噪声 diff
- [ ] 1.7 CI 数据库矩阵（D12/D17）：backend-test 增 PostgreSQL 16 service 轨（DATABASE_URL 注入）为主流真实库轨，行锁/并发防重类用例标 `@pytest.mark.pg_only`（SQLite 轨跳过）；MySQL 8.0 兼容轨每周 nightly。验证：PG 轨全绿且 pg_only 收集数 > 0；nightly 可手动触发
  - [x] 1.7a CI 已有 PG 16 service 轨，但只跑迁移（`backend-migrate-postgres`：upgrade → 核对列类型 → downgrade → 再 upgrade），尚未跑 pytest 全量用例
  - [ ] 1.7b 全量用例在 PG 轨上跑 + `@pytest.mark.pg_only` 标记体系（当前未实现）；MySQL nightly 未实现
- [ ] 1.8 覆盖率基线：dev 依赖加 pytest-cov，CI 输出总覆盖率并生成 README 徽章。验证：徽章渲染，阈值先设当前值只降不升
- [ ] 1.9 可观测性最小集：`GET /healthz`（探活含 DB 连通）；请求级结构化访问日志（uvicorn access log 加 request_id 字段）；财务写入与反结账进既有审计口径；docs 补一页部署运维（PG 备份 `pg_dump`/恢复步骤）。验证：compose 环境下 healthz 200、日志可 grep request_id、备份命令实跑一次成功

## 2. Phase 1 · 财务内核 + 凭证引擎（3-4 周，本期核心）

- [ ] 2.0 2.1 整改（D10/D14，前置）：凭证域金额 Float → `Numeric(18,2)` + Decimal，消除 EPS 浮点比较；凭证号改期间序列 `JV-{yyyyMM}-{seq}`；`create_voucher` 对缺失 accountId 给显式 BusinessError；`account_balances` 返回 Decimal。验证：新增「0.1+0.2 精确等于 0.3」类断言，14 个存量用例适配后全绿
  - [x] 2.0a 金额口径：按 D10 的 2026-09-26 修正，范围已从凭证域扩大到全部 7 个金额列；EPS 与两处 `1e-9` 删除，借贷平衡改精确比较；`account_balances` 返回 Decimal；量化入口 `app/common/money.py`
  - [x] 2.0b 断言：新增 `3×0.1 + HALF_UP(0.125) = 0.43` 与「借贷差 1 分拒过账」两条回归；金额类断言由 `pytest.approx` 改精确比较（适配面：`test_finance_service.py` + `test_accounting_core.py`，130 passed）
  - [ ] 2.0c 凭证号仍为 `JV-YYYYMMDD-XXX`（走 `generate_order_no`），未改为 D14 的期间序列 `JV-{yyyyMM}-{seq}`
  - [ ] 2.0d `create_voucher` 对缺失 `accountId` 的分录现在抛 `KeyError`（`line["accountId"]`），未改成显式 `BusinessError`
- [x] 2.1 数据模型：`account`（科目树）、`voucher`/`voucher_line`、`period`，含状态机与约束；建表迁移/初始化脚本。验证：pytest 覆盖科目树构建、非明细科目拒绝记账
- [ ] 2.2 会计内核 API + 前端页：科目表维护、凭证列表/详情/手工录入、过账/冲销、期间结账/反结账。验证：posted 凭证改删返回 409；红字冲销双向关联；closed 期间写入被拒；借贷不平过账被拒（spec: accounting-core 全 Scenario）
- [ ] 2.3 凭证引擎：`posting_rule/rule_line/account_mapping` 三表 + `generate_voucher()`；幂等键 `(event_type, doc_type, doc_id)`；规则试算接口。验证：同事件重复触发只出一张凭证；试算不落库（spec: voucher-engine Req 1 全 Scenario）
- [ ] 2.4 事件接入第一批：出库确认（应收+收入+成本结转）、收款核销（银行对应收）；与现有业务事务绑定，失败整单回滚。验证：发货后凭证号回写出库单；停用收入科目后发货失败且库存不变（原子性专测）
- [ ] 2.5 报表：科目余额表、利润表、资产负债表、试算平衡检查；项目下钻明细账。验证：随机业务序列 property-based 测试断言「资产=负债+权益」恒等；10 笔标准业务手工核对表与报表输出一致
- [ ] 2.6 前端财务一级菜单信息架构 + 报表页 ECharts/表格；Phase 1 发布：Release v0.1 + 演示站更新 + GIF「发货→凭证→利润表变化」。验证：E2E 走通该主链路

## 3. Phase 2 · 业务链补全（3 周）

- [ ] 3.1 采购域：采购订单/入库/采购发票，入库暂估事件接入凭证引擎；应付与付款核销。验证：采购→暂估→发票→付款全链路凭证正确、幂等
- [ ] 3.2 费用单（报销/日常费用）+ 费用科目映射。验证：费用凭证进利润表费用项
- [ ] 3.3 移动加权平均成本：出库成本口径统一由库存流水 `cost_amount` 提供，引擎取数；与批次 FIFO 口径差异写入 docs。验证：连续出入库序列下加权成本手工核对一致
- [ ] 3.4 期末结转损益（`PERIOD_CLOSE` 内置规则）+ 结账前检查流。验证：结转后损益科目余额清零、本年利润金额等于当期利润表营业利润（勾稽断言）；已结转期间反结账留审计日志

## 4. Phase 3 · AI 层（3 周）

- [ ] 4.1 `app/ai/` 平台层（D13）：LlmClient 适配（OpenAI 兼容 + Ollama，async httpx + 超时重试）、`AI_ENABLED` 开关、`ai_draft`/`ai_audit_log` 表、草稿确认框架、管理端模型配置与用量页。验证：mock LLM 单测通过；关开关后 AI 路由 503、其余功能回归全绿
- [ ] 4.2 ChatBI：3 个语义视图（销售毛利/应收账龄/库存快照）+ 查询计划 JSON Schema + 参数化模板执行器；多轮会话上下文；前端对话面板（ECharts 渲染、点击追问）。验证：mock LLM 下 10 个标准问题集查询计划正确；越界问题拒答且不执行查询（spec: chatbi 全 Scenario）
- [ ] 4.3 票据入账：上传与视觉解析、要素+置信度确认页、往来单位模糊匹配（歧义必选）、确认过账与附件追溯。验证：样例票据集（5 张标准图）端到端 E2E；解析失败路径不产生正式单据
- [ ] 4.4 Phase 3 发布：Release v0.3 + README 增补 AI 章节（明确「AI 永不直接写财务数据」边界声明）+ 两段演示 GIF。验证：演示站配置 mock LLM 后可离线演示全部 AI 流程

## 5. Phase 4 · 审计 Agent 与运营（持续）

- [ ] 5.1 异常审计 Agent：月末扫描凭证/库存流水，检出科目误用、期末大额调账、借贷异常模式，产出带理由的体检报告（只读，不生成草稿）。验证：注入 5 类典型异常样例，召回率 100%、误报有人工复核标注
- [ ] 5.2 传播与社区：掘金/V2EX 发布「凭证引擎设计」深文；每个 Release 写 changelog；收集首批 issue 反馈定 v0.4 范围
