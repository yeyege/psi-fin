import api from './client'

export interface PageData<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

// ============ 商品 SKU ============

export interface Product {
  id: number
  name: string
  sku: string
  fnsKu: string | null
  caseQty: number
  unit: string
  width: number
  height: number
  length: number
  weight: number
  status: string
  createdAt: string
  updatedAt: string
}

export interface ProductPayload {
  name: string
  sku: string
  fnsKu?: string | null
  caseQty?: number
  unit?: string
  width?: number
  height?: number
  length?: number
  weight?: number
}

export const getProducts = (params: { keyword?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<Product> }>('/products', { params })

export const getProduct = (id: number) =>
  api.get<any, { code: number; data: Product }>(`/products/${id}`)

export const createProduct = (data: ProductPayload) =>
  api.post<any, { code: number; data: Product }>('/products', data)

export const updateProduct = (id: number, data: Partial<ProductPayload> & { status?: string }) =>
  api.put<any, { code: number; data: Product }>(`/products/${id}`, data)

export const deleteProduct = (id: number) => api.delete(`/products/${id}`)


// ============ 客户（分层 A/B/C） ============

export interface Customer {
  id: number
  code: string
  name: string
  tier: string
  contact: string | null
  phone: string | null
  status: string
  createdAt: string
  updatedAt: string
}

export interface CustomerPayload {
  code: string
  name: string
  tier?: string
  contact?: string | null
  phone?: string | null
}

export const getCustomers = (params: { keyword?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<Customer> }>('/customers', { params })

export const getCustomer = (id: number) =>
  api.get<any, { code: number; data: Customer }>(`/customers/${id}`)

export const createCustomer = (data: CustomerPayload) =>
  api.post<any, { code: number; data: Customer }>('/customers', data)

export const updateCustomer = (id: number, data: Partial<CustomerPayload> & { status?: string }) =>
  api.put<any, { code: number; data: Customer }>(`/customers/${id}`, data)

export const deleteCustomer = (id: number) => api.delete(`/customers/${id}`)


// ============ 数据看板 ============

export interface DashboardSummary {
  todayInboundCount: number
  todayOutboundCount: number
  pendingInboundCount: number
  pendingOutboundCount: number
  totalInventoryQty: number
  lowStockProductCount: number
  activeProductCount: number
  activeCustomerCount: number
}

export const getDashboardSummary = () =>
  api.get<any, { code: number; data: DashboardSummary }>('/dashboard/summary')


// ============ 仓库 / 库区 / 库位 ============

export interface Warehouse {
  id: number
  code: string
  name: string
  status: string
}

export interface Zone {
  id: number
  warehouseId: number
  code: string
  name: string
  zoneType: string
}

export interface Location {
  id: number
  zoneId: number
  warehouseId: number
  code: string
  priority: number
  status: string
}

export const getWarehouses = () =>
  api.get<any, { code: number; data: Warehouse[] }>('/warehouses')

export const createWarehouse = (data: { code: string; name: string }) =>
  api.post<any, { code: number; data: Warehouse }>('/warehouses', data)

export const getZones = (warehouseId?: number) =>
  api.get<any, { code: number; data: Zone[] }>('/zones', { params: { warehouseId } })

export const createZone = (data: { warehouseId: number; code: string; name: string; zoneType?: string }) =>
  api.post<any, { code: number; data: Zone }>('/zones', data)

export const getLocations = (params: { warehouseId?: number; zoneId?: number }) =>
  api.get<any, { code: number; data: Location[] }>('/locations', { params })

export const createLocation = (data: { zoneId: number; warehouseId: number; code: string; priority?: number }) =>
  api.post<any, { code: number; data: Location }>('/locations', data)


// ============ 库存（可用 + 锁定） ============

export interface InventoryRow {
  productId: number
  productName: string
  sku: string
  availableQty: number
  lockedQty: number
  totalQty: number
  warehouseId: number
  warehouseName: string
  updatedAt: string
  // location 视图额外字段
  locationCode?: string
  batchNo?: string | null
}

export interface FlowRow {
  id: number
  flowType: string
  orderType: string
  orderNo: string
  productId: number
  productName: string
  sku: string
  locationCode: string | null
  batchNo: string | null
  quantity: number
  beforeQty: number | null
  afterQty: number | null
  remark: string | null
  createdAt: string
}

export interface BatchRow {
  id: number
  batchNo: string
  productId: number
  productName: string
  sku: string
  inboundDate: string
  manufactureDate: string | null
  expiryDate: string | null
}

export const getInventory = (params: {
  view?: 'product' | 'location'
  keyword?: string
  warehouseId?: number
  batchNo?: string
  page?: number
  pageSize?: number
}) =>
  api.get<any, { code: number; data: PageData<InventoryRow> }>('/inventory', { params })

export const getFlows = (params: {
  orderNo?: string
  productId?: number
  locationCode?: string
  flowType?: string
  page?: number
  pageSize?: number
}) =>
  api.get<any, { code: number; data: PageData<FlowRow> }>('/inventory/flows', { params })

export const getBatches = (params: { keyword?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<BatchRow> }>('/inventory/batches', { params })


// ============ 入库单（PENDING → COMPLETED） ============

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
  batchNo?: string | null
}

export interface InboundOrder {
  id: number
  orderNo: string
  supplierName: string
  status: string
  remark?: string | null
  items: InboundOrderItem[]
  createdAt: string
}

export const createInboundOrder = (data: { supplierName: string; items: InboundItemRequest[]; remark?: string }) =>
  api.post<any, { code: number; data: InboundOrder }>('/inbound-orders', data)

export const receiveInboundOrder = (id: number) =>
  api.post<any, { code: number; data: InboundOrder }>(`/inbound-orders/${id}/receive`)

export const getInboundOrders = (params: { status?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<InboundOrder> }>('/inbound-orders', { params })

export const getInboundOrder = (id: number) =>
  api.get<any, { code: number; data: InboundOrder }>(`/inbound-orders/${id}`)


// ============ 出库单（PENDING → PICKED → SHIPPED） ============

export interface OutboundItemRequest {
  productId: number
  quantity: number
  locationCode: string
}

export interface OutboundOrderItem {
  productId: number
  productName: string
  quantity: number
  locationCode: string
}

export interface OutboundOrder {
  id: number
  orderNo: string
  customerName: string
  status: string
  remark?: string | null
  items: OutboundOrderItem[]
  createdAt: string
}

export const createOutboundOrder = (data: { customerName: string; items: OutboundItemRequest[]; remark?: string }) =>
  api.post<any, { code: number; data: OutboundOrder }>('/outbound-orders', data)

export const pickOutboundOrder = (id: number) =>
  api.post<any, { code: number; data: OutboundOrder }>(`/outbound-orders/${id}/pick`)

export const reviewOutboundOrder = (id: number) =>
  api.post<any, { code: number; data: OutboundOrder }>(`/outbound-orders/${id}/review`)

export const shipOutboundOrder = (id: number) =>
  api.post<any, { code: number; data: OutboundOrder }>(`/outbound-orders/${id}/ship`)

export const getOutboundOrders = (params: { status?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<OutboundOrder> }>('/outbound-orders', { params })


// ============ 退货管理（FBA / 买家 / 服务商） ============

export interface ReturnItemRequest {
  productId: number
  quantity: number
  locationCode: string
  disposition: string
}

export interface ReturnOrderItem {
  productId: number
  productName: string
  quantity: number
  locationCode: string
  disposition: string
  batchNo?: string | null
}

export interface ReturnOrder {
  id: number
  orderNo: string
  customerId: number
  customerName: string
  source: string
  status: string
  remark?: string | null
  items: ReturnOrderItem[]
  createdAt: string
}

export const createReturnOrder = (data: { customerId: number; source: string; items: ReturnItemRequest[]; remark?: string }) =>
  api.post<any, { code: number; data: ReturnOrder }>('/returns', data)

export const receiveReturnOrder = (id: number) =>
  api.post<any, { code: number; data: ReturnOrder }>(`/returns/${id}/receive`)

export const finishReturnOrder = (id: number) =>
  api.post<any, { code: number; data: ReturnOrder }>(`/returns/${id}/finish`)

export const getReturnOrders = (params: { status?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<ReturnOrder> }>('/returns', { params })


// ============ 波次拣货（智能波次策略） ============

export interface PickingOrderItem {
  productId: number
  productName: string
  quantity: number
  locationCode: string
}

export interface PickingOrderRow {
  id: number
  pickingNo: string
  waveId: number
  outboundOrderId: number
  outboundOrderNo: string
  status: string
  createdAt: string
  items: PickingOrderItem[]
}

export interface Wave {
  id: number
  waveNo: string
  status: string
  remark?: string | null
  createdAt: string
  pickingOrders: PickingOrderRow[]
}

export const createWave = (data: { outboundOrderIds: number[]; remark?: string }) =>
  api.post<any, { code: number; data: Wave }>('/waves', data)

export const getWaves = (params: { status?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<Wave> }>('/waves', { params })

export const getPickingOrders = (params: { waveId?: number; status?: string; page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<PickingOrderRow> }>('/waves/picking-orders', { params })

export const pickPickingOrder = (id: number) =>
  api.post<any, { code: number; data: PickingOrderRow }>(`/waves/picking-orders/${id}/pick`)


// ============ 库内作业：移库 / 库存调整 ============

export interface TransferItemRequest {
  productId: number
  quantity: number
  fromLocationCode: string
  toLocationCode: string
}

export interface TransferItem {
  productId: number
  productName: string
  quantity: number
  fromLocationCode: string
  toLocationCode: string
}

export interface TransferOrder {
  id: number
  orderNo: string
  status: string
  remark?: string | null
  items: TransferItem[]
  createdAt: string
}

export const createTransfer = (data: { items: TransferItemRequest[]; remark?: string }) =>
  api.post<any, { code: number; data: TransferOrder }>('/transfers', data)

export const getTransfers = (params: { page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<TransferOrder> }>('/transfers', { params })

export interface AdjustmentItemRequest {
  productId: number
  locationCode: string
  changeQty: number
}

export interface AdjustmentItem {
  productId: number
  productName: string
  locationCode: string
  changeQty: number
}

export interface AdjustmentOrder {
  id: number
  orderNo: string
  status: string
  remark?: string | null
  items: AdjustmentItem[]
  createdAt: string
}

export const createAdjustment = (data: { items: AdjustmentItemRequest[]; remark?: string }) =>
  api.post<any, { code: number; data: AdjustmentOrder }>('/adjustments', data)

export const getAdjustments = (params: { page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<AdjustmentOrder> }>('/adjustments', { params })


// ============ 用户与鉴权 ============

export interface UserInfo {
  id: number
  username: string
  role: 'admin' | 'operator'
  status: string
  createdAt: string
}

export const login = (data: { username: string; password: string }) =>
  api.post<any, { code: number; message: string; data: { token: string; user: UserInfo } }>('/auth/login', data)

export const logout = () =>
  api.post<any, { code: number; message: string }>('/auth/logout')

export const getMe = () =>
  api.get<any, { code: number; data: UserInfo }>('/auth/me')

export const getUsers = (params: { page?: number; pageSize?: number }) =>
  api.get<any, { code: number; data: PageData<UserInfo> }>('/users', { params })

export const createUser = (data: { username: string; password: string; role: 'admin' | 'operator' }) =>
  api.post<any, { code: number; data: UserInfo }>('/users', data)

export const updateUser = (id: number, data: { password?: string; role?: 'admin' | 'operator'; status?: string }) =>
  api.put<any, { code: number; data: UserInfo }>(`/users/${id}`, data)

export const deleteUser = (id: number) =>
  api.delete<any, { code: number }>(`/users/${id}`)
