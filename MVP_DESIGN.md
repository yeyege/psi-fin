# MVP 里程碑设计（M1-M7 · 历史设计文档）

> 定位：本文是 **MVP 阶段（M1-M7）的设计文档**，当时按「活文档」维护。M1-M7 已全部交付完成，
> 本文转为**历史设计记录**：保留至今仍然有效的架构设计与开发规范，移除已过时的进度快照与面试交付期内容。
> - 当前任务与进展 → [TASKS.md](./TASKS.md)（进展实录）
> - 待办与阶段规划总入口 → 本地规划文档 `docs/ROADMAP_TODO.md`（暂未入库）
> - 面试交付期检查清单、2026-08 进度快照原文 → 本地归档 `docs/interview/MVP_DESIGN-历史归档.md`（未入库）

---

## 一、里程碑范围与交付状态（M1-M7，全部 ✅）

| 里程碑 | 内容 | 状态 | 落点 |
|---|---|---|---|
| M1 客户管理 | Customer 表（A/B/C 分层），出库/退货归属客户，CRUD + 软删除 | ✅ | `routers/customers.py` |
| M2 商品扩展 | FNSKU + 箱规 `case_qty` | ✅ | `models` + `routers/products.py` |
| M3 数据看板 | 出入库单量 / 库存总量 / 低库存 / 待处理单据统计卡片 | ✅ | `routers/dashboard.py` |
| M4 退货管理 | 退货单（FBA/买家/服务商），转正品 / 换标 / 报废三种处置 | ✅ | `routers/returns.py` |
| M5 波次拣货 | 出库单聚合生成波次，拣货单按库位优先级排序 + 锁定库存 | ✅ | `routers/waves.py` |
| M6 复核验货 | 发货前强制复核：`PICKED → REVIEWED → SHIPPED` | ✅ | `routers/outbound.py` |
| M7 用户权限 | User/Role（admin/operator）、PBKDF2-SHA256、Token 鉴权、路由守卫 | ✅ | `routers/auth.py`、`auth_service` |

> 交付之后项目继续演进：盘点闭环（P0-1）、业财一体收入侧闭环（销售订单 → 应收 → 核销 → 账龄 → 驾驶舱）、
> Vercel/Neon/Pages 部署体系。这些**不在本文 MVP 范围内**，见 TASKS.md 与 ROADMAP_TODO.md。

## 二、架构设计（仍然有效）

### 2.1 分层

```
routers(接口) → services(业务/事务/状态机) → models(ORM) → SQLite/MySQL/PostgreSQL
                └── inventory_service 统一库存入口（add/deduct/lock/ship + 强制流水）
```

### 2.2 核心数据模型

```
Product ── Inventory(product, location, batch, avail/locked) ── InventoryFlow
Customer ── ReturnOrder ─ ReturnItem（收货：转正品→inventory / 报废）
Wave ── PickingOrder ── PickingItem（含推荐库位）── OutboundOrder
User ── Role
```

### 2.3 单据状态机

| 单据 | 状态机 |
|---|---|
| 入库单 | `PENDING(待收货) → COMPLETED(已收货上架)`，创建不触碰库存 |
| 出库单 | `PENDING → PICKED(拣货锁定) → REVIEWED(已复核) → SHIPPED(发货扣减)` |
| 退货单 | `PENDING → RECEIVED(收货登记) → DONE(换标/转正品/报废)` |
| 波次 | `CREATED → PICKING → COMPLETED` |
| 拣货单 | `CREATED → PICKING → PICKED(锁定完成)`，与出库单 PICKED 联动 |

## 三、开发规范（长期强制约定）

1. **契约**：Schema 用 `CamelModel`（`alias_generator=to_camel`），前后端 camelCase 统一。
2. **单号**：`generate_order_no(db, Model, prefix)`，前缀如 `IN` / `RT`(退货) / `WV`(波次) / `PK`(拣货)。
3. **库存**：一切库存变动走 `inventory_service` 统一入口，强制写 `inventory_flow` 流水（记录变动前/后数量）。
4. **事务**：多表写操作单事务，失败整单回滚；库存不足先 SUM 校验后操作，配合行锁 + 条件 UPDATE 防超卖。
5. **性能**：列表查询 joinedload 防 N+1，筛选列建索引，服务端分页。
6. **测试**：每模块后端 `pytest` 覆盖状态机 + 异常分支；前端关键纯函数 vitest；业财模块另见会计内核测试规范。
7. **提交**：小步提交，中文 Conventional Commits（`feat(backend): …` / `fix: …` / `test: …`），一个模块一个 commit。

## 四、当年预留、尚未实现的方向（以 ROADMAP 为准）

MVP 设计时在 P1/P2 预留过：计费与多货主、箱级库存、物流商对接（`erp_adapter`/`carrier_adapter`）、PDA 移动端、
Redis 缓存 / MQ 削峰、多语言时区等。**这些是否推进、优先级如何，一律以本地规划文档 `docs/ROADMAP_TODO.md` 的 P0-P3 表为准**，本文不再维护待办。
