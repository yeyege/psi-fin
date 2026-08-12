# API 接口规范（最终实现版）

> 本文档为最终实现对应的接口约定（对标领星 WMS 重构后）。
> 统一约定：请求/响应字段均为 **camelCase**（`supplierName`、`availableQty`），后端通过 `CamelModel` 基类自动转换。

Base URL: `http://localhost:8000/api`

---

## 通用约定

- 请求体：`application/json`
- 响应体：

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

- 业务错误：HTTP 状态码（400 参数/业务错误、404 不存在、409 库存不足），`detail` 为中文提示。
- 分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": { "list": [], "total": 100, "page": 1, "pageSize": 20 }
}
```

- 单号格式：`IN-YYYYMMDD-XXX`（入库）、`OUT-YYYYMMDD-XXX`（出库）、`MV-YYYYMMDD-XXX`（移库）、`ADJ-YYYYMMDD-XXX`（调整）、`RT-YYYYMMDD-XXX`（退货）、`WV-YYYYMMDD-XXX`（波次）、`PK-YYYYMMDD-XXX`（拣货单），各类型独立日递增序列。
- 鉴权：`Authorization: Bearer <token>`（登录后签发，默认有效期 7 天）；需要管理员的操作（用户管理）返回 403。

---

## 1. 商品 SKU

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/api/products` | 商品列表（?keyword=&page=&pageSize=） |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/products` | 新增商品 |
| PUT | `/api/products/{id}` | 更新商品 |
| DELETE | `/api/products/{id}` | 删除商品（有库存则 400 拒绝） |

商品字段：`name`、`sku`、`fnsKu`（FNSKU）、`caseQty`（每箱数量）、`unit`、`width`、`height`、`length`、`weight`、`status(ACTIVE/INACTIVE)`。

## 1.1 客户管理

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/api/customers` | 客户列表（?keyword=&page=&pageSize=） |
| GET | `/api/customers/{id}` | 客户详情 |
| POST | `/api/customers` | 新增客户 |
| PUT | `/api/customers/{id}` | 更新客户 |
| DELETE | `/api/customers/{id}` | 删除客户（软删除 status=INACTIVE） |

客户字段：`code`（唯一）、`name`、`tier(A/B/C)`、`contact`、`phone`、`status`。

## 1.2 数据看板

```
GET /api/dashboard/summary
```

返回：`todayInbound`（今日入库单数）、`todayOutbound`（今日出库单数）、`pendingOrders`（待处理单据）、`totalStock`（库存总量）、`lowStockCount`（低库存商品数 <10）、`activeProductCount`、`customerCount`。

## 2. 仓库 / 库区 / 库位

| 方法 | URL | 说明 |
|------|-----|------|
| GET/POST | `/api/warehouses` | 仓库列表 / 新增（code、name） |
| GET/POST | `/api/zones` | 库区列表（?warehouseId=）/ 新增（warehouseId、code、name、zoneType: GOODS/DEFECT） |
| GET/POST | `/api/locations` | 库位列表（?warehouseId=&zoneId=）/ 新增（zoneId、warehouseId、code、priority） |

> 层级：仓库 → 库区（正品/残次）→ 库位（带优先级，越大越优先推荐上架）。

## 3. 入库单（状态机：PENDING → COMPLETED）

### 3.1 创建入库单（PENDING，不改变库存）

```
POST /api/inbound-orders
```

```json
{
  "supplierName": "供应商A",
  "remark": "可选",
  "items": [
    { "productId": 1, "quantity": 100, "locationCode": "A-01-01" },
    { "productId": 2, "quantity": 50, "locationCode": "A-01-02" }
  ]
}
```

### 3.2 收货上架（PENDING → COMPLETED）

```
POST /api/inbound-orders/{id}/receive
```

> 收货时在同一事务内：为每个明细行生成批次（`batchNo = {单号}-{明细id}`）→ 累加库存（available）→ 写 INBOUND 流水 → 回填明细 batchId。

### 3.3 列表 / 详情

```
GET /api/inbound-orders?status=&page=&pageSize=
GET /api/inbound-orders/{id}
```

响应 data.items 含 `batchNo`（收货后回填）。

## 4. 库存查询（可用量 available + 锁定量 locked）

```
GET /api/inventory?view=product|location&keyword=&warehouseId=&batchNo=&page=&pageSize=
```

| 参数 | 说明 |
|------|------|
| view | `product`（默认，按 商品+仓库 汇总） / `location`（按库位批次明细） |
| keyword | 商品名称或 SKU 模糊搜索 |
| warehouseId / batchNo | 仓库 / 批次筛选 |

product 视图行：`productId, productName, sku, availableQty, lockedQty, totalQty, warehouseId, warehouseName, updatedAt`
location 视图行：额外含 `locationCode, batchNo`。

> 低库存（totalQty < 10）由前端高亮。

## 5. 库存流水（全量可追溯）

```
GET /api/inventory/flows?orderNo=&flowType=&locationCode=&page=&pageSize=
```

流水类型 `flowType`：`INBOUND` 入库收货 / `OUTBOUND` 出库发货 / `PICK_LOCK` 拣货锁定 / `MOVE_OUT` 移库出 / `MOVE_IN` 移库入 / `ADJUST_IN` 调整盘盈 / `ADJUST_OUT` 调整盘亏 / `RETURN_IN` 退货收货回补。

行字段：`flowType, orderType, orderNo, productId, productName, sku, locationCode, batchNo, quantity, beforeQty, afterQty, remark, createdAt`。

## 6. 批次

```
GET /api/inventory/batches?keyword=&page=&pageSize=
```

行字段：`batchNo, productId, productName, sku, inboundDate, manufactureDate, expiryDate`。

## 7. 出库单（状态机：PENDING → PICKED → REVIEWED → SHIPPED）

### 7.1 创建（PENDING，不改变库存）

```
POST /api/outbound-orders
```

```json
{
  "customerName": "客户X",
  "remark": "可选",
  "items": [
    { "productId": 1, "quantity": 10, "locationCode": "A-01-01" }
  ]
}
```

### 7.2 拣货（PENDING → PICKED，原子锁定防超卖）

```
POST /api/outbound-orders/{id}/pick
```

> available → locked 逐行原子锁定；任一明细库存不足 → 409，整单回滚，状态保持 PENDING。

### 7.3 复核验货（PICKED → REVIEWED，发货前置环节）

```
POST /api/outbound-orders/{id}/review
```

> 未复核直接发货返回 409；复核不改变库存。

### 7.4 发货（REVIEWED → SHIPPED，扣减锁定）

```
POST /api/outbound-orders/{id}/ship
```

### 7.5 列表

```
GET /api/outbound-orders?status=&page=&pageSize=
```

## 8. 库内作业

### 8.1 移库（立即完成）

```
POST /api/transfers
GET  /api/transfers?page=&pageSize=
```

```json
{
  "remark": "可选",
  "items": [
    { "productId": 1, "quantity": 10, "fromLocationCode": "A-01-01", "toLocationCode": "A-02-01" }
  ]
}
```

> 源库位扣减（MOVE_OUT）→ 目标库位增加（MOVE_IN），双向流水；库存不足 409 整单回滚。

### 8.2 库存调整（立即完成）

```
POST /api/adjustments
GET  /api/adjustments?page=&pageSize=
```

```json
{
  "remark": "可选",
  "items": [
    { "productId": 1, "locationCode": "A-01-01", "changeQty": 5 }
  ]
}
```

> `changeQty > 0` 盘盈（ADJUST_IN）/ `< 0` 盘亏（ADJUST_OUT）；盘亏不足 409 整单回滚。

## 9. 退货管理（状态机：PENDING → RECEIVED → DONE）

```
POST /api/return-orders                # 创建退货单（PENDING）
GET  /api/return-orders?status=&page=&pageSize=
```

创建请求体：

```json
{
  "customerName": "客户X",
  "source": "FBA_SELLER_CARRIER",
  "remark": "可选",
  "items": [
    { "productId": 1, "quantity": 5, "locationCode": "A-01-01", "disposition": "RESELL" }
  ]
}
```

- `source`：FBA 退件 / 买家退件 / 服务商退件；`disposition`：`RESELL` 转正品 / `RELABEL` 换标 / `SCRAP` 报废。
- 收货：`POST /api/return-orders/{id}/receive`（RECEIVED）——RESELL/RELABEL 生成批次 + 回补可用库存 + `RETURN_IN` 流水，SCRAP 只登记；`POST /api/return-orders/{id}/finish`（DONE）。

## 10. 波次拣货

```
POST /api/waves                          # 聚合出库单生成波次
GET  /api/waves?status=&page=&pageSize=
GET  /api/waves/picking-orders?waveId=&status=&page=&pageSize=
POST /api/waves/picking-orders/{id}/pick # 拣货：锁定库存，波次状态随进度推进
```

创建波次请求体：`{ "outboundOrderIds": [1, 2], "remark": "可选" }`。

- 波次状态：`CREATED → PICKING → COMPLETED`；拣货单状态：`CREATED → PICKED`。
- 拣货明细按「商品,库位」聚合、按库位优先级降序排序（PDA 推荐路径）；库存不足 409 整单回滚。

## 11. 用户与鉴权

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/api/auth/login` | 登录，返回 `{ token, user }`（body: username/password） |
| POST | `/api/auth/logout` | 退出，当前 token 失效 |
| GET | `/api/auth/me` | 当前登录用户（需登录） |
| GET | `/api/users` | 用户列表（仅 admin） |
| POST | `/api/users` | 新增用户（仅 admin；username/password≥6位/role: admin\|operator） |
| PUT | `/api/users/{id}` | 更新用户（仅 admin；password/role/status） |
| DELETE | `/api/users/{id}` | 删除用户（仅 admin；最后一个启用管理员不可删） |

- 未登录访问受保护接口返回 401；非 admin 调用用户管理返回 403；重复用户名 409。
- 默认账号：`admin / admin123`（服务启动时自动创建）。

---

## 数据库核心表（重构后）

- `warehouse`（code, name）/ `zone`（warehouse_id, zone_type: GOODS/DEFECT）/ `location`（zone_id, warehouse_id, code, priority）
- `product`（name, sku, fns_ku, case_qty, unit, width, height, length, weight, status）
- `customer`（code 唯一, name, tier: A/B/C, contact, phone, status）
- `batch`（batch_no, product_id, inbound_date, manufacture_date, expiry_date）
- `inventory`：唯一键 `uk_product_location_batch (product_id, location_code, batch_id)`，字段 `available_qty` + `locked_qty`，索引 `location_code`、`product_id`
- `inventory_flow`（flow_type, order_type, order_no, product_id, location_code, batch_id, quantity, before_qty, after_qty, remark）
- `inbound_orders` / `inbound_order_items`（含 batch_id 回填）
- `outbound_orders` / `outbound_order_items`（含 wave_id，状态含 REVIEWED）
- `return_orders` / `return_order_items`（source, disposition）
- `waves` / `picking_orders` / `picking_order_items`
- `stock_transfers` / `stock_adjustments`
- `users`（username 唯一, password_hash, role: admin/operator, status）/ `auth_tokens`（token 唯一, user_id, expires_at）
