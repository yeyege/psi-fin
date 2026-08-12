# WMS 测试 — 交付验证文档

> 复核时间：2026-08-12　环境：Windows / Python 3.11+ / Node 20+ / SQLite（`wms.db` 启动时自动生成，不入库）
> 说明：`README.md` / `TASKS.md` 为面试方需求文件；本文件与 `NOTES.md` 为交付方实际开发与验证记录。

---

## 一、单元测试验证（交付前实测）

| 范围 | 命令 | 结果 |
|---|---|---|
| 后端 pytest | `cd backend-python && uv run pytest` | **76 passed**（55.3s） |
| 前端 vitest | `cd frontend-vue && npx vitest run` | **14 passed**（0.6s） |

### 后端分文件用例统计（10 个文件，共 76 例）

| 测试文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `test_inventory_service.py` | 10 | 入库累加/新建行、跨批次 FIFO 扣减、库存不足无副作用、锁定+发货、商品/库位双视图、筛选、流水追溯 |
| `test_inbound_service.py` | 6 | 创建不改库存、收货生成批次与流水、重复收货拒绝、商品/库位不存在、单号递增 |
| `test_outbound_service.py` | 11 | 拣货锁定、库存不足 409、发货扣减、未拣货/未复核不可发货、部分失败整单回滚、locked 归零对账、并发双线程防超卖 |
| `test_transfer_adjustment.py` | 5 | 移库双向流水、移库不足回滚、调整盘盈/盘亏、盘亏不足回滚 |
| `test_auth_service.py` | 14 | 密码哈希与校验、登录/登出、token 校验与过期、用户 CRUD 权限、最后 admin 保护 |
| `test_api_auth.py` | 4 | 未登录 401、无效 token、登录态访问、operator 不可管理用户 |
| `test_customer_product.py` | 9 | 客户 CRUD/软删除、商品 FNSKU+箱规、camelCase 映射 |
| `test_dashboard.py` | 3 | 看板聚合（今日单量/库存总量/低库存） |
| `test_return_service.py` | 8 | 退货收货回补/报废不补、重复收货拒绝、单号递增 |
| `test_wave_service.py` | 6 | 波次生成拣货单、按库位优先级排序、拣货锁定推进、库存不足回滚 |
| **合计** | **76** | |

### 前端（vitest，14 例）

`src/utils/inventory.test.ts`：`isLowStock` 阈值边界（<10 高亮）、`totalOf` 兜底、`filterByKeyword`（名称/SKU/大小写/空）、`filterByWarehouse`、`lowStockRowClass`。

---

## 二、一键启动验证（开发期间实测，见 NOTES.md）

- **后端**：`cd backend-python && uv run uvicorn app.main:app --port 8000`
  - lifespan 自动建表 + 种子数据（仓库/库区/库位/商品/客户/用户）
  - 默认账号 `admin / admin123`；API 文档 http://localhost:8000/docs
- **前端**：`cd frontend-vue && npm run dev` → http://localhost:5173（/api 代理到 8000）
- **端到端联调**：入库 → 收货 → 出库 → 拣货 → 复核 → 发货 → 移库 → 调整 → 流水 → 批次，库存数字链路自洽。

---

## 三、工程化验证（记录于 NOTES.md / git 提交）

| 项 | 验证方式 | 结果 |
|---|---|---|
| Docker Compose | `docker compose up -d --build`（mysql + backend + frontend/nginx） | ✅ 一键全栈，已验证（提交 7272ab7） |
| Playwright E2E | `cd frontend-vue && npm run test:e2e`（入库核心正向流程） | ✅ 本机实测通过 |
| GitHub Actions CI | push 触发：pytest + 前端 build/vitest + docker build 校验 | ✅ 配置就绪（`.github/workflows/ci.yml`） |

---

## 四、任务完成度对照（TASKS.md）

| 任务 | 状态 | 实现与说明 |
|---|---|---|
| 必做 1 入库单创建 | ✅ | 单号 `IN-YYYYMMDD-XXX`、多行明细、仓库→库位级联、事务保证一致性 |
| 必做 2 库存查询 | ✅ | 商品/库位双视图、SKU/仓库/库位筛选、服务端分页、低库存（<10）红色高亮 |
| 必做 3 Bug 修复 | ✅ | 后端：删除商品校验关联库存（软删除保流水）；前端：编辑返回保留页码 |
| 选做 A 出库+防超卖 | ✅ | `available/locked` 分离 + 原子条件 UPDATE（`WHERE available >= take`），并发测试覆盖 |
| 选做 B 单元测试 | ✅ | 后端 76 例 + 前端 14 例 |
| 选做 C 前端性能优化 | ✅ | 服务端分页 + 300ms 搜索防抖 + 筛选纯函数抽离 |
| MVP M1-M7 | ✅ | 客户管理 / 商品 FNSKU+箱规 / 数据看板 / 退货管理 / 波次拣货 / 复核验货 / 用户权限 |

---

## 五、已知边界与说明

1. **并发防超卖**：SQLite 无行锁，采用「先 SUM 校验总量 + 逐行条件 UPDATE」保证并发下不超卖；生产库切换 PostgreSQL 后 `FOR UPDATE` 行锁语义生效。
2. **入库语义**：创建单据（PENDING）不触碰库存，**收货上架时**才生成批次并累加库存（对标领星两段式，避免单据作废后库存失真）。
3. **FIFO 扣减为近似**：按 `Inventory.id` 升序（≈批次创建顺序）先扣早期批次，严格批次管理可按入库日期排序。
4. **本机 `wms.db` 不入 git**：启动时自动生成，评审方一键启动即可复现完整数据环境。
