# WMS 全局待办总览（ROADMAP / TODO）

> 本文档是项目级**总待办入口**：汇总核心功能 P0-P3 阶段进度、openspec change 资产状态、以及下一步指向。详细单点方案/待办见对应 openspec change 或 NOTES.md。
> 维护约定：每完成一个阶段或 change 后同步更新本表。

---

## 一、核心功能阶段进度（对照 NOTES.md 第十章 P0-P3）

排序原则：先「正确性与数据可信」→ 再「作业效率与性能」→ 后「系统能力与架构」→ 最后「集成与扩展」。

### P0 — 正确性与数据可信

| # | 项目 | 状态 | 关联资产 |
|---|---|---|---|
| 1 | 盘点闭环（Cycle Count：4 种范围快照 / 实盘录入 / 自动盘盈盘亏 / 准确率指标） | 已完成 | git db50f09；NOTES.md §P0-1 |
| 2 | **严格批次 FIFO + 效期管理**（扣减按效期优先 FEFO、临期/过期/呆滞预警） | [x] 待办已设计，待实施 | openspec change `p0-2-strict-fifo-expiry` |
| 3 | 复核扫码验货（扫码枪/PDA 逐件校验 SKU+批次+数量） | 待办（未设计） | — |
| 4 | PostgreSQL 行锁 + 实时对账（行锁代码已有，对账任务缺失；PG 迁移属 P2-10） | 待办 | — |

### P1 — 作业效率与系统性能

| # | 项目 | 状态 |
|---|---|---|
| 5 | 波次策略引擎（按类型/时效/承运商聚合 + S 形路径优化；现有为 M5 基础波次） | 待办 |
| 6 | 上架与补货策略（库位利用率/周转率推荐 + 自动补货建议；现有为库位优先级推荐） | 待办 |
| 7 | 前端性能与看板升级（虚拟滚动未做；趋势折线/环形图/热力图已上线） | 部分完成（看板✅ / 虚拟滚动待办） |

### P2 — 系统能力与架构升级

| # | 项目 | 状态 |
|---|---|---|
| 8 | RBAC 细粒度权限（角色-权限-资源 + 审计日志；现有 M7 简版 admin/operator） | 待办 |
| 9 | Redis 缓存 + 消息队列削峰（热商品/看板缓存、入库出库 MQ 异步化） | 待办 |
| 10 | 数据库升级 PostgreSQL（现 SQLite/MySQL；行锁/备份/监控告警） | 待办 |

### P3 — 集成与扩展

| # | 项目 | 状态 |
|---|---|---|
| 11 | ERP/TMS/电商平台集成（API 网关 + Webhook + 幂等补偿） | 待办 |
| 12 | 多货主/多仓库/3PL 计费 | 待办 |
| 13 | PDA / 移动端 H5（扫码收货/上架/拣货/复核/盘点） | 待办 |
| 14 | 序列号与质检（QC） | 待办 |
| 15 | 运营报表与预警推送（热力图/效率排行/邮件企微推送） | 待办 |

---

## 二、openspec change 资产状态

| change | 范围 | 规划产物 | 实施进度 | 状态 / 下一步 |
|---|---|---|---|---|
| `bi-dashboard-apple-style` | Apple Store 风格 BI 看板原型（preview/） | proposal/specs/design/tasks ✅ | 23/23 | complete；**待 archive**（沉淀主 specs） |
| `business-console-demo` | 业财一体中后台方案演示页（preview/） | proposal/specs/design/tasks ✅ | 6/8 | in-progress；剩余 2.2 对外文案 QA、2.3 窄屏可用性 |
| `p0-2-strict-fifo-expiry` | P0-2 严格 FIFO + 效期管理（backend + frontend） | proposal/specs/design/tasks ✅ | 0/13 | planning complete；**下一步实施（/opsx:apply）** |

---

## 三、下一步行动

1. **实施 P0-2**：进入 openspec change `p0-2-strict-fifo-expiry` 执行 `/opsx:apply`（先后端排序+状态计算+单测，再前端展示与回归）。这是 P0 唯一未动的"数据可信"项。
2. **收尾 `business-console-demo`**：完成 2.2 文案 QA、2.3 窄屏检查后归档。
3. **归档 `bi-dashboard-apple-style`**：`openspec archive` 将已完成能力沉淀到主 specs，消除当前 `openspec/specs/` 为空的状态。
4. 之后回到 P0-3（复核扫码）、P0-4（对账任务），再进入 P1。

---

## 四、其他待办 / 维护项

- [ ] `preview/`、`openspec/`、`.claude/` 目前为 git untracked，需决定提交或归档策略
- [ ] 视图 Mock 汇总卡在对应后端接口就绪后逐步替换为真实统计（沿用 SummaryCards 组件约定）
- [ ] 临期/呆滞阈值（30/180 天）当前为后端模块常量，后续可配置化

---

## 相关文档

- [NOTES.md](../NOTES.md)：开发说明、AI 使用沉淀、遇到的问题与 P0-P3 规划详述
- [MVP_DESIGN.md](../MVP_DESIGN.md)：MVP 里程碑（M1-M7）历史设计文档，保留仍有效的架构/规范（交付期旧清单仅本地留存）
- [TASKS.md](../TASKS.md)：任务与进展实录（以仓库真实代码为准；历史题面仅本地留存）
- `openspec/changes/*/tasks.md`：各 change 的实施待办
