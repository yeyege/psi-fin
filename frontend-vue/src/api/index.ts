import api from './client'

// ============ 商品（参考实现） ============

export interface Product {
  id: number
  name: string
  sku: string
  unit: string
  createdAt: string
  updatedAt: string
}

export const getProducts = (keyword?: string) =>
  api.get<any, { code: number; data: Product[] }>('/products', { params: { keyword } })

export const getProduct = (id: number) =>
  api.get<any, { code: number; data: Product }>(`/products/${id}`)

export const createProduct = (data: { name: string; sku: string; unit?: string }) =>
  api.post('/products', data)

export const updateProduct = (id: number, data: { name: string; unit?: string }) =>
  api.put(`/products/${id}`, data)

export const deleteProduct = (id: number) =>
  api.delete(`/products/${id}`)


// ============ 仓库 & 库位 ============

export interface Warehouse {
  id: number
  code: string
  name: string
}

export interface Location {
  id: number
  warehouseId: number
  code: string
  status: string
}

export const getWarehouses = () =>
  api.get<any, { code: number; data: Warehouse[] }>('/warehouses')

export const getLocations = (warehouseId: number) =>
  api.get<any, { code: number; data: Location[] }>(`/warehouses/${warehouseId}/locations`)


// ============ 库存查询（任务2） ============

export interface InventoryItem {
  productId: number
  productName: string
  sku: string
  locationCode: string
  warehouseName: string
  quantity: number
  updatedAt: string
}

export interface PageData<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export const getInventory = (params: {
  keyword?: string
  warehouseId?: number
  locationCode?: string
  page?: number
  pageSize?: number
}) =>
  api.get<any, { code: number; data: PageData<InventoryItem> }>('/inventory', { params })


// ============ 入库单（任务1） ============

export interface InboundItemRequest {
  productId: number
  quantity: number
  locationCode: string
}

export interface InboundOrderItem {
  productId: number
  productName: string
  quantity: number
  locationCode: string
}

export interface InboundOrder {
  id: number
  orderNo: string
  supplierName: string
  status: string
  items: InboundOrderItem[]
  createdAt: string
}

export const createInboundOrder = (data: {
  supplierName: string
  items: InboundItemRequest[]
}) => api.post<any, { code: number; data: InboundOrder }>('/inbound-orders', data)

export const getInboundOrders = (params: { page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<InboundOrder> }>('/inbound-orders', { params })

export const getInboundOrder = (id: number) =>
  api.get<any, { code: number; data: InboundOrder }>(`/inbound-orders/${id}`)


// ============ 出库单（选做 A） ============

export interface OutboundItemRequest {
  productId: number
  quantity: number
  locationCode: string
}

export interface OutboundOrder {
  id: number
  orderNo: string
  customerName: string
  status: string
  items: InboundOrderItem[]
  createdAt: string
}

export const createOutboundOrder = (data: {
  customerName: string
  items: OutboundItemRequest[]
}) => api.post<any, { code: number; data: OutboundOrder }>('/outbound-orders', data)

export const getOutboundOrders = (params: { page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<OutboundOrder> }>('/outbound-orders', { params })
