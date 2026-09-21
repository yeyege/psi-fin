# 任务与进展实录（TASKS）

> 定位：本文件记录项目**实际完成了什么、正在做什么**，所有条目以仓库真实代码与测试为准，可逐条核查。
> 历史说明：根目录旧版 TASKS.md 是最初面试题的题面，与项目实际演进已严重脱节（"待实现"项早已完成或过时），
> 原文已归档至本地 `docs/interview/TASKS-原始题面.md`（历史私密材料，未入库），仅作历史叙事保留，**不再作为进度依据**。
> 待办总入口见本地规划文档 `docs/ROADMAP_TODO.md`（暂未入库），本文不重复维护待办清单。

---

## 一、已交付里程碑

### 1. 基础仓储闭环（源自早期测试题范围，已全部落地并扩展）

| 任务 | 实际交付 | 佐证 |
|---|---|---|
| 入库单 | 单号 `IN-YYYYMMDD-XXX` 自动生成；创建不动库存，**收货时**事务内生成批次 + 累加库存 + 写流水；状态机 `PENDING → COMPLETED` | `app/services/inbound_service.py` |
| 库存查询 | 按商品汇总 / 按库位明细双视图；模糊搜索 + 仓库筛选 + 批次筛选；服务端分页；低库存（<10）整行红色高亮；300ms 搜索防抖 | `app/routers/inventory.py`、`InventoryView.vue` |
| 出库 + 防超卖 | `PENDING → PICKED(锁定) → REVIEWED(复核) → SHIPPED(扣减)`；行锁 + 条件 UPDATE + 整单回滚；并发双线程防超卖测试 | `outbound_service.py`、`tests/test_outbound_service.py` |
| Bug 修复 | ① 商品删除前校验关联库存（改软删除）② 列表编辑后保留当前页码 | `NOTES.md` |

### 2. MVP 扩展（M1-M7，对标领星跨境仓储系统）

客户分层 A/B/C · 商品 FNSKU/箱规 · 数据看板 · 退货（转正品/换标/报废）· 波次拣货 · 复核验货 · admin/operator 权限与 Token 鉴权。
详见 [MVP_DESIGN.md](./MVP_DESIGN.md)。

### 3. 业财一体（收入侧闭环，超出原题面的自主演进）

- 销售订单：草稿 → 确认 → 发货 → 完成/作废，确认后明细锁定
- 发货自动生成应收（幂等由 DB 唯一约束兜底）→ 收款核销（部分核销/预收）→ 应收余额与账龄 → 经营驾驶舱
- 会计内核：凭证/科目（COA）体系，`tests/test_accounting_core.py` 覆盖

### 4. 工程化与交付

- 测试：**后端 126 + 前端 31 = 157+ 自动化用例**，另有 4 条 Playwright E2E
- CI：GitHub Actions（pytest + build/vitest + docker build）
- 部署：Vercel Serverless + Neon PostgreSQL（真后端演示）；GitHub Pages（纯前端 Mock 演示）；Docker Compose 一键全栈

---

## 二、当前进行中

- **P0-2 严格批次 FIFO + 效期管理（FEFO）**：规划已完成（openspec change `p0-2-strict-fifo-expiry`），实施 0/13，按其 tasks.md 推进。

后续阶段（P0-3 复核扫码、P0-4 实时对账、P1/P2/P3）统一见本地规划文档 `docs/ROADMAP_TODO.md`（暂未入库）。

---

## 三、边界声明（避免误读）

本项目为**轻量级**进销存 · 业财一体化中后台，聚焦库存底座 + 销售订单 + 应收 + 经营分析；
**未实现**：采购管理、应付、总账/报表三表、成本核算完整链路、多货主计费。原题目或宣传材料中与此冲突的描述，以本声明为准。
