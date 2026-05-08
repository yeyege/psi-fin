# API 接口规范

> 本文档定义了前后端接口约定。你可以在 AI 辅助下按此规范实现。

Base URL: `http://localhost:{port}/api`

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

- 错误响应：

```json
{
  "code": 400,
  "message": "商品不存在",
  "data": null
}
```

- 分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "pageSize": 20
  }
}
```

---

## 1. 商品（已实现，作为参考）

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/api/products` | 商品列表（支持 ?keyword=&page=&pageSize=） |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/products` | 新增商品 |
| PUT | `/api/products/{id}` | 更新商品 |
| DELETE | `/api/products/{id}` | 删除商品 |

---

## 2. 仓库 & 库位（已实现，作为参考）

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/api/warehouses` | 仓库列表 |
| GET | `/api/warehouses/{id}/locations` | 某仓库下的库位列表 |

---

## 3. 入库单（待实现 — 任务 1）

### 3.1 创建入库单

```
POST /api/inbound-orders
```

**Request Body:**

```json
{
  "supplierName": "供应商A",
  "items": [
    {
      "productId": 1,
      "quantity": 100,
      "locationCode": "WH-A-01-01"
    },
    {
      "productId": 2,
      "quantity": 50,
      "locationCode": "WH-A-01-02"
    }
  ]
}
```

**Response (201):**

```json
{
  "code": 201,
  "message": "入库单创建成功",
  "data": {
    "id": 1,
    "orderNo": "IN-20260508-001",
    "supplierName": "供应商A",
    "status": "COMPLETED",
    "items": [
      {
        "productId": 1,
        "productName": "商品A",
        "quantity": 100,
        "locationCode": "WH-A-01-01"
      }
    ],
    "createdAt": "2026-05-08T10:00:00"
  }
}
```

### 3.2 入库单列表

```
GET /api/inbound-orders?page=1&pageSize=20
```

### 3.3 入库单详情

```
GET /api/inbound-orders/{id}
```

---

## 4. 库存查询（待实现 — 任务 2）

```
GET /api/inventory?keyword=&warehouseId=&page=1&pageSize=20
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 商品名称或 SKU 模糊搜索 |
| warehouseId | int | 否 | 仓库 ID 筛选 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页条数，默认 20，最大 100 |

**Response:**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "productId": 1,
        "productName": "蓝牙耳机",
        "sku": "SKU-001",
        "locationCode": "WH-A-01-01",
        "warehouseName": "广州主仓",
        "quantity": 100,
        "updatedAt": "2026-05-08T09:30:00"
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 20
  }
}
```

---

## 5. 出库单（选做 A）

```
POST /api/outbound-orders
```

**Request Body:**

```json
{
  "customerName": "客户X",
  "items": [
    {
      "productId": 1,
      "quantity": 10,
      "locationCode": "WH-A-01-01"
    }
  ]
}
```

> 注意：出库涉及库存扣减，需处理并发安全问题。

---

## 数据库表结构（参考）

```sql
-- 商品表
CREATE TABLE products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    unit VARCHAR(20) DEFAULT '个',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 仓库表
CREATE TABLE warehouses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL
);

-- 库位表
CREATE TABLE locations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    warehouse_id BIGINT NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'FREE',
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

-- 库存表
CREATE TABLE inventory (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    location_code VARCHAR(50) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE KEY uk_product_location (product_id, location_code)
);

-- 入库单主表
CREATE TABLE inbound_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(50) NOT NULL UNIQUE,
    supplier_name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 入库单明细表
CREATE TABLE inbound_order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    location_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES inbound_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 出库单主表
CREATE TABLE outbound_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 出库单明细表
CREATE TABLE outbound_order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    location_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES outbound_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```
