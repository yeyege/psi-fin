# 任务与进展实录（TASKS）

> 定位：本文件记录项目**实际完成了什么、正在做什么**，所有条目以仓库真实代码与测试为准，可逐条核查。
> 历史说明：根目录旧版 TASKS.md 是最初面试题的题面，与项目实际演进已严重脱节（"待实现"项早已完成或过时），
> 原文已归档至本地 `docs/interview/_归档/TASKS-原始题面.md`（历史私密材料，未入库），仅作历史叙事保留，**不再作为进度依据**。
> 待办总入口见 [`docs/roadmap/`](./docs/roadmap/README.md)（五阶段主干 README + 内部执行明细 ROADMAP_TODO），本文不重复维护待办清单。

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
- 会计内核：凭证/科目（COA）体系，`tests/test_accounting_core.py` 覆盖（**仅 models + service**，尚未挂 router）

### 4. 工程化与交付

- 测试：**后端 145 + 前端 31 = 176 自动化用例**（2026-10-04 实测：`uv run pytest` → 145 passed；`npm test` → 31 passed / 3 文件），另有 Playwright E2E（本轮为后端改动未跑，**用例数待实测**，不手抄）
- CI：GitHub Actions（pytest + build/vitest + docker build）
- 部署：Vercel Serverless + Neon PostgreSQL（真后端演示）；GitHub Pages（纯前端 Mock 演示）；Docker Compose 一键全栈

---

## 二、当前进行中

> 进度数以 `openspec list --json` 实测为准（2026-10-04 刷新）。

- **开源业财一体演进（openspec change `oss-finance-ai-platform`）**：8/35。Phase 1 仅 2.0 + 2.1 落地；**尚无 router 与前端页**（`routers/` 无 `accounting.py`、`main.py` 未挂载）→ §一.3 所述「会计内核」目前未对外暴露；Phase 3 AI 层（`app/ai/`）未开工。含两条待裁定的 spec/代码冲突（C2 主库口径、C3 D10 旧文本未删；C1 凭证号已于 2026-10-04 按 D14 修正收口），见 [`docs/roadmap/ROADMAP_TODO.md`](./docs/roadmap/ROADMAP_TODO.md) §三。
- **P0-2 严格批次 FIFO + 效期管理（FEFO）**：**已开工（1/12）**（openspec change `p0-2-strict-fifo-expiry`）。组 1 已落：`inventory_service.batch_lifecycle()` 批次生命周期纯函数 + `tests/test_batch_expiry.py`；**FEFO 扣减排序未动**，`inventory_service.py` L203 / L262 / L318 仍按改造前的 `Inventory.id`。剩余范围以该 change `proposal.md` 顶部状态行为准。

后续阶段（P0-3 复核扫码、P0-4 实时对账、P1/P2/P3）统一见 [`docs/roadmap/ROADMAP_TODO.md`](./docs/roadmap/ROADMAP_TODO.md)。

---

## 三、边界声明（避免误读）

本项目为**轻量级**进销存 · 业财一体化中后台，聚焦库存底座 + 销售订单 + 应收 + 经营分析；
**未实现**：采购管理、应付、总账/报表三表、成本核算完整链路、多货主计费。原题目或宣传材料中与此冲突的描述，以本声明为准。
