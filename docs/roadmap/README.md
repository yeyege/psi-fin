# 业财一体 + AI 开源项目 · Roadmap 总入口

> 本文件夹是项目 **roadmap / 待办的唯一 Markdown 入口**。
> **主干 = 对外 OSS 五阶段路线图**（业财一体 + AI 企业级开源 ERP）；
> 内部工程质量整改与业务功能执行明细挂在 [`./ROADMAP_TODO.md`](./ROADMAP_TODO.md)。

## 一、核心命题

从「已有进销存底座」到「中小企业进销存 + 财务核算 + AI 助手一体化开源 ERP」——
**任何业务单据，经规则驱动的凭证引擎自动生成财务凭证，实时进报表。**

## 二、五阶段主干路线

以 Phase 为发布单元控制范围：每阶段必须产出一个「一句话演示」，做不完的功能砍进下个 Phase，不阻塞发布。
**完成度不在此手抄**，一律以下面「事实源」列的 `tasks.md` 复选框为准。

| Phase | 目标（一句话） | 状态 | 事实源（任务级复选框） |
|---|---|---|---|
| **0 开源门面** | Apache-2.0 / README / 一键 seed / Alembic 接线 / CI 数据库矩阵 / 覆盖率徽章 | 起步（工具链部分就位） | [tasks §1](../../openspec/changes/oss-finance-ai-platform/tasks.md) |
| **1 财务内核** | 科目/凭证/期间状态机 + 凭证引擎（规则表驱动）+ 利润表/资产负债表 | 进行中（本期核心，2.1 已交付） | [tasks §2](../../openspec/changes/oss-finance-ai-platform/tasks.md) |
| **2 业务链补全** | 采购/入库/应付 + 费用单 + 移动加权成本 + 期末结转锁账 | 待办 | [tasks §3](../../openspec/changes/oss-finance-ai-platform/tasks.md) |
| **3 AI 层** | LlmClient 适配 + ChatBI 语义问数 + 票据→草稿凭证 + ai_draft 确认框架 | 待办 | [tasks §4](../../openspec/changes/oss-finance-ai-platform/tasks.md) |
| **4 Agent 与运营** | 异常审计 Agent（只读体检）+ 凭证模板插件 + 社区 Release | 持续 | [tasks §5](../../openspec/changes/oss-finance-ai-platform/tasks.md) |

## 三、视图分工（谁是什么的事实源）

同一套路线有三份呈现，各有边界，**改口径先改本 README，再同步派生视图**：

- **任务级事实源**：[`openspec/changes/oss-finance-ai-platform/tasks.md`](../../openspec/changes/oss-finance-ai-platform/tasks.md)
  —— 逐条复选框，`code-review` 的 Spec 轴以此为据，**不迁出、不并入本文件夹**。
- **对外可视化**：[`site/business-finance-roadmap.html`](../../site/business-finance-roadmap.html)
  —— GitHub Pages 部署产物（在线：<https://yeyege.github.io/psi-fin/business-finance-roadmap.html>）。
  受 `deploy-pages.yml` 只发布 `site/` 的约束，**保留原位**，其内容是本索引的派生视图。
- **规格原文**：[`openspec/changes/oss-finance-ai-platform/`](../../openspec/changes/oss-finance-ai-platform/)（proposal · design · specs）。

## 四、内部执行明细

- [`./ROADMAP_TODO.md`](./ROADMAP_TODO.md)：全局待办双轨 —— **A 轨工程质量整改**（Q1-Q15：Alembic、Decimal、日志、CI 守门、前端重构、文档一致性）+ **B 轨核心业务功能**（P0-P3：FIFO/效期、波次、RBAC、PG、集成）。
- 与主干的关系：A 轨的数据完整性项（Q1 Alembic / Q2 Decimal）是 Phase 0/1 的前置；B 轨的财务相关项已并入五阶段主干执行。

## 五、数字口径

测试数量、覆盖率等**只认根 [`../../README.md`](../../README.md) 与 CI 徽章**，本文件夹不硬编码，避免腐烂
（依据 [`../../AGENTS.md`](../../AGENTS.md) §4「用例数量不在本文件维护，以实际运行输出为准」）。

## 六、相关文档

- [`../PRD.md`](../PRD.md) / [`../API_SPEC.md`](../API_SPEC.md) / [`../GLOSSARY.md`](../GLOSSARY.md)
- [`../../TASKS.md`](../../TASKS.md)：任务与进展实录
- [`../../VERIFICATION.md`](../../VERIFICATION.md)：交付验证记录
