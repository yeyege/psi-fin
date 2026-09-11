/**
 * 纯前端演示用的内存数据与业务规则
 *
 * 口径与后端 `backend-python/app/services/finance_service.py` 保持一致:
 * - 只有【发货】才生成应收,同一订单不重复生成(幂等)
 * - 收款支持部分核销/结清;单张应收禁止超额核销;收款可大于核销额,差额为预收余额
 * - 账龄【以到期日为基准】分段
 * - 驾驶舱金额与应收台账同源
 *
 * 数据在内存中,刷新页面即重置,保证演示可重复。
 */

export interface MockCustomer { id: number; code: string; name: string }
export interface MockProduct { id: number; name: string; sku: string; unit: string; price: number }
export interface MockOrderItem { productId: number; productName: string; quantity: number; unitPrice: number; amount: number }
export interface MockOrder {
  id: number
  orderNo: string
  customerId: number
  customerName: string
  status: string // DRAFT / CONFIRMED / SHIPPED / COMPLETED / CANCELLED
  creditDays: number
  totalAmount: number
  outboundOrderNo: string | null
  shippedAt: string | null
  remark: string | null
  items: MockOrderItem[]
  createdAt: string
}
export interface MockEntry {
  id: number
  entryNo: string
  entryType: string // RECEIVABLE / RECEIPT
  partnerType: string
  partnerId: number | null
  partnerName: string
  sourceOrderNo: string | null
  amount: number
  settledAmount: number
  occurredDate: string
  dueDate: string | null
  status: string // OPEN / PARTIAL / SETTLED
  remark: string | null
  createdAt: string
}
export interface MockSettlement { receiptEntryId: number; targetEntryId: number; amount: number }
export interface MockState {
  customers: MockCustomer[]
  products: MockProduct[]
  orders: MockOrder[]
  entries: MockEntry[]
  settlements: MockSettlement[]
  seq: { order: number; entry: number }
}

// ============ 日期与金额工具 ============

export const round2 = (n: number) => Math.round((Number(n) || 0) * 100) / 100

const pad = (n: number) => String(n).padStart(2, '0')

export const fmtDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const fmtDateTime = (d: Date) =>
  `${fmtDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

export const todayStr = () => fmtDate(new Date())

export const addDays = (dateStr: string, days: number) => {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + days)
  return fmtDate(d)
}

/** 账龄分段(以到期日为基准),与后端 _aging_bucket 一致 */
export const agingBucket = (dueDate: string | null, today = todayStr()) => {
  if (!dueDate) return 'notDue'
  if (dueDate >= today) return 'notDue'
  const days = Math.floor((new Date(`${today}T00:00:00`).getTime() - new Date(`${dueDate}T00:00:00`).getTime()) / 86400000)
  if (days <= 30) return 'days1to30'
  if (days <= 60) return 'days31to60'
  return 'days60plus'
}

export const outstandingOf = (e: MockEntry) => round2(e.amount - e.settledAmount)

export const deriveStatus = (amount: number, settled: number) => {
  if (settled <= 0) return 'OPEN'
  if (settled + 1e-9 >= amount) return 'SETTLED'
  return 'PARTIAL'
}

// ============ 初始演示数据 ============

export function createInitialState(): MockState {
  const today = todayStr()
  const customers: MockCustomer[] = [
    { id: 1, code: 'CUST-A01', name: '杭州云集电商' },
    { id: 2, code: 'CUST-A02', name: '广州鲜途贸易' },
    { id: 3, code: 'CUST-B01', name: '上海味选优选' },
  ]
  const products: MockProduct[] = [
    { id: 1, name: '蓝月亮洗衣液 3kg', sku: 'P-001', unit: '瓶', price: 88 },
    { id: 2, name: '维达抽纸 24包', sku: 'P-002', unit: '箱', price: 45 },
    { id: 3, name: '农夫山泉 550ml×24', sku: 'P-003', unit: '箱', price: 60 },
    { id: 4, name: '金龙鱼调和油 5L', sku: 'P-004', unit: '桶', price: 128 },
    { id: 5, name: '蒙牛纯牛奶 250ml×24', sku: 'P-005', unit: '箱', price: 72 },
    { id: 6, name: '海天金标生抽 1.9L', sku: 'P-006', unit: '瓶', price: 25 },
  ]

  const state: MockState = { customers, products, orders: [], entries: [], settlements: [], seq: { order: 0, entry: 0 } }

  const mkItems = (rows: Array<[number, number]>): MockOrderItem[] =>
    rows.map(([pid, qty]) => {
      const p = products.find((x) => x.id === pid)!
      return { productId: p.id, productName: p.name, quantity: qty, unitPrice: p.price, amount: round2(qty * p.price) }
    })

  /** 造一张订单(seed 用):给定状态与发货日期,日期用"相对今天"偏移 */
  const seedOrder = (opts: {
    customerId: number; status: string; creditDays: number; shipOffset?: number; createdOffset: number;
    rows: Array<[number, number]>; remark?: string;
  }) => {
    const customer = customers.find((c) => c.id === opts.customerId)!
    const items = mkItems(opts.rows)
    state.seq.order += 1
    const order: MockOrder = {
      id: state.seq.order,
      orderNo: `SO-${today.replace(/-/g, '')}-${String(state.seq.order).padStart(3, '0')}`,
      customerId: customer.id,
      customerName: customer.name,
      status: opts.status,
      creditDays: opts.creditDays,
      totalAmount: round2(items.reduce((s, i) => s + i.amount, 0)),
      outboundOrderNo: null,
      shippedAt: opts.shipOffset === undefined ? null : fmtDateTime(new Date(`${addDays(today, -opts.shipOffset)}T10:30:00`)),
      remark: opts.remark ?? null,
      items,
      createdAt: fmtDateTime(new Date(`${addDays(today, -opts.createdOffset)}T09:20:00`)),
    }
    state.orders.push(order)
    // 已发货订单:按规则生成应收
    if (order.status === 'SHIPPED' || order.status === 'COMPLETED') {
      generateReceivable(state, order)
    }
    return order
  }

  // 覆盖四种账龄段与"未发货无应收"的演示场景
  seedOrder({ customerId: 1, status: 'SHIPPED', creditDays: 30, shipOffset: 40, createdOffset: 42, rows: [[1, 3], [2, 2]] })  // 到期=today-10 → 逾期1-30
  seedOrder({ customerId: 2, status: 'SHIPPED', creditDays: 15, shipOffset: 80, createdOffset: 82, rows: [[4, 1]] })           // 到期=today-65 → 逾期60+
  seedOrder({ customerId: 3, status: 'SHIPPED', creditDays: 30, shipOffset: 10, createdOffset: 12, rows: [[5, 4]] })           // 到期=today+20 → 未到期
  seedOrder({ customerId: 1, status: 'SHIPPED', creditDays: 0, shipOffset: 45, createdOffset: 47, rows: [[6, 10]] })           // 到期=today-45 → 逾期31-60
  seedOrder({ customerId: 2, status: 'SHIPPED', creditDays: 30, shipOffset: 3, createdOffset: 4, rows: [[3, 5]] })             // 到期=today+27 → 未到期
  seedOrder({ customerId: 2, status: 'DRAFT', creditDays: 30, createdOffset: 1, rows: [[3, 2]] })                              // 草稿:无应收
  seedOrder({ customerId: 3, status: 'CONFIRMED', creditDays: 15, createdOffset: 2, rows: [[1, 1]] })                          // 已确认未发货:无应收

  // 演示部分核销与结清:AR1 部分收 100;AR3 全额结清
  const ar1 = state.entries.find((e) => e.entryNo.endsWith('-001'))!
  const ar3 = state.entries.find((e) => e.entryNo.endsWith('-003'))!
  applyReceipt(state, { partnerName: ar1.partnerName, amount: 100, occurredDate: addDays(today, -30), allocations: [{ targetEntryId: ar1.id, amount: 100 }] })
  applyReceipt(state, { partnerName: ar3.partnerName, amount: ar3.amount, occurredDate: addDays(today, -5), allocations: [{ targetEntryId: ar3.id, amount: ar3.amount }] })

  return state
}

// ============ 单号 ============

export const nextOrderNo = (state: MockState) => {
  state.seq.order += 1
  return `SO-${todayStr().replace(/-/g, '')}-${String(state.seq.order).padStart(3, '0')}`
}

export const nextEntryNo = (state: MockState, prefix: string) => {
  state.seq.entry += 1
  return `${prefix}-${todayStr().replace(/-/g, '')}-${String(state.seq.entry).padStart(3, '0')}`
}

// ============ 业务规则 ============

/** 生成应收(幂等):同一订单只生成一条 */
export function generateReceivable(state: MockState, order: MockOrder): MockEntry {
  const existing = state.entries.find((e) => e.sourceOrderNo === order.orderNo && e.entryType === 'RECEIVABLE')
  if (existing) return existing

  const occurred = (order.shippedAt || fmtDateTime(new Date())).slice(0, 10)
  const entry: MockEntry = {
    id: state.entries.length ? Math.max(...state.entries.map((e) => e.id)) + 1 : 1,
    entryNo: nextEntryNo(state, 'AR'),
    entryType: 'RECEIVABLE',
    partnerType: 'CUSTOMER',
    partnerId: order.customerId,
    partnerName: order.customerName,
    sourceOrderNo: order.orderNo,
    amount: order.totalAmount,
    settledAmount: 0,
    occurredDate: occurred,
    dueDate: addDays(occurred, order.creditDays || 0),
    status: 'OPEN',
    remark: `销售订单 ${order.orderNo} 发货生成`,
    createdAt: fmtDateTime(new Date()),
  }
  state.entries.push(entry)
  return entry
}

export interface ReceiptInput {
  partnerName: string
  amount: number
  occurredDate?: string
  remark?: string
  allocations?: Array<{ targetEntryId: number; amount: number }>
}

/** 把一笔收款的未核销余额核销到应收(支持部分核销);校验失败抛错且不产生任何副作用 */
export function allocateReceipt(
  state: MockState,
  receiptId: number,
  allocations: Array<{ targetEntryId: number; amount: number }>,
): MockEntry {
  const receipt = state.entries.find((e) => e.id === receiptId && e.entryType === 'RECEIPT')
  if (!receipt) throw new Error('收款流水不存在')

  const remaining = round2(receipt.amount - receipt.settledAmount)
  const totalAlloc = round2(allocations.reduce((s, a) => s + round2(a.amount), 0))
  if (totalAlloc > remaining + 1e-9) {
    throw new Error(`核销金额 ${totalAlloc} 超过该笔收款未核销余额 ${remaining}`)
  }

  // 先整体校验(只读),避免半途失败留下半个结果
  for (const a of allocations) {
    const target = state.entries.find((e) => e.id === a.targetEntryId)
    if (!target) throw new Error(`应收流水不存在: ${a.targetEntryId}`)
    if (target.entryType !== 'RECEIVABLE') throw new Error('只能核销到应收流水')
    if (round2(a.amount) <= 0) throw new Error('核销金额必须大于 0')
    const outstanding = outstandingOf(target)
    if (round2(a.amount) > outstanding + 1e-9) {
      throw new Error(`核销金额 ${round2(a.amount)} 超过应收 ${target.entryNo} 未结余额 ${outstanding}`)
    }
  }

  for (const a of allocations) {
    const target = state.entries.find((e) => e.id === a.targetEntryId)!
    state.settlements.push({ receiptEntryId: receipt.id, targetEntryId: target.id, amount: round2(a.amount) })
    target.settledAmount = round2(target.settledAmount + round2(a.amount))
    target.status = deriveStatus(target.amount, target.settledAmount)
  }
  receipt.settledAmount = round2(receipt.settledAmount + totalAlloc)
  receipt.status = deriveStatus(receipt.amount, receipt.settledAmount)
  return receipt
}

/** 收款登记(可同时核销)。到账金额可大于核销金额,差额保留为该笔收款的未核销余额(预收) */
export function applyReceipt(state: MockState, input: ReceiptInput): MockEntry {
  const amount = round2(input.amount)
  if (amount <= 0) throw new Error('收款金额必须大于 0')

  const receipt: MockEntry = {
    id: state.entries.length ? Math.max(...state.entries.map((e) => e.id)) + 1 : 1,
    entryNo: nextEntryNo(state, 'RC'),
    entryType: 'RECEIPT',
    partnerType: 'CUSTOMER',
    partnerId: null,
    partnerName: input.partnerName,
    sourceOrderNo: null,
    amount,
    settledAmount: 0,
    occurredDate: input.occurredDate || todayStr(),
    dueDate: null,
    status: 'OPEN',
    remark: input.remark ?? null,
    createdAt: fmtDateTime(new Date()),
  }
  state.entries.push(receipt)

  if (input.allocations?.length) {
    allocateReceipt(state, receipt.id, input.allocations)
  }
  return receipt
}

// ============ 单例状态(刷新即重置) ============

let currentState: MockState | null = null

export const getState = (): MockState => {
  if (!currentState) currentState = createInitialState()
  return currentState
}

export const resetState = () => {
  currentState = createInitialState()
}
