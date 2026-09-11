/**
 * 纯前端 Mock 适配器 — 让站点在没有后端的情况下也能完整演示业财闭环
 *
 * 用法:client.ts 中当 VITE_USE_MOCK==='true' 时挂到 axios 实例的 adapter 上;
 * 命中路由由本地实现响应(返回与后端一致的结构 `{code, message, data}`),
 * 未覆盖的接口走兜底,避免旧页面因缺接口而崩溃。
 */
import type { AxiosAdapter, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import {
  getState, applyReceipt, allocateReceipt, generateReceivable, nextOrderNo, outstandingOf, agingBucket, round2,
  addDays, fmtDateTime, todayStr,
  type MockEntry, type MockOrder,
} from './data'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

const makeResponse = (config: AxiosRequestConfig, data: any, message = 'success', status = 200): AxiosResponse => ({
  data: { code: status, message, data },
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  headers: {},
  config: config as InternalAxiosRequestConfig,
})

class MockHttpError extends Error {
  response: AxiosResponse
  isAxiosError = true
  constructor(config: AxiosRequestConfig, message: string, status = 400) {
    super(message)
    this.response = makeResponse(config, null, message, status)
  }
}

const pageOf = <T>(rows: T[], page: number, pageSize: number) => ({
  list: rows.slice((page - 1) * pageSize, page * pageSize),
  total: rows.length,
  page,
  pageSize,
})

interface Ctx {
  config: AxiosRequestConfig
  method: string
  path: string
  params: Record<string, any>
  body: any
  match: RegExpMatchArray
}

type Handler = (ctx: Ctx) => any

// ============ 响应构造(与后端字段保持一致) ============

const orderResp = (o: MockOrder) => ({
  id: o.id, orderNo: o.orderNo, customerId: o.customerId, customerName: o.customerName,
  status: o.status, creditDays: o.creditDays, totalAmount: round2(o.totalAmount),
  outboundOrderNo: o.outboundOrderNo, shippedAt: o.shippedAt, remark: o.remark,
  items: o.items.map((i) => ({ ...i, amount: round2(i.amount), unitPrice: round2(i.unitPrice) })),
  createdAt: o.createdAt,
})

const entryResp = (e: MockEntry) => {
  const today = todayStr()
  const outstanding = outstandingOf(e)
  return {
    id: e.id, entryNo: e.entryNo, entryType: e.entryType, partnerType: e.partnerType,
    partnerId: e.partnerId, partnerName: e.partnerName, sourceOrderNo: e.sourceOrderNo,
    amount: round2(e.amount), settledAmount: round2(e.settledAmount), outstanding,
    occurredDate: e.occurredDate, dueDate: e.dueDate, status: e.status,
    overdue: !!(e.dueDate && e.dueDate < today && outstanding > 0),
    remark: e.remark, createdAt: e.createdAt,
  }
}

// ============ 路由表 ============

const routes: Array<{ method: string; re: RegExp; handler: Handler }> = [
  // ---- 鉴权 ----
  {
    method: 'POST', re: /^\/auth\/login$/, handler: () => ({
      token: 'mock-token',
      user: { id: 1, username: 'admin', role: 'admin', status: 'ACTIVE', createdAt: fmtDateTime(new Date()) },
    }),
  },
  {
    method: 'GET', re: /^\/auth\/me$/, handler: () => ({
      id: 1, username: 'admin', role: 'admin', status: 'ACTIVE', createdAt: fmtDateTime(new Date()),
    }),
  },

  // ---- 基础数据(供下拉选择) ----
  {
    method: 'GET', re: /^\/customers$/, handler: ({ params }) => {
      const st = getState()
      const rows = st.customers.map((c) => ({
        id: c.id, code: c.code, name: c.name, tier: 'A', contact: null, phone: null,
        status: 'ACTIVE', createdAt: fmtDateTime(new Date()), updatedAt: fmtDateTime(new Date()),
      }))
      return pageOf(rows, Number(params.page) || 1, Number(params.pageSize) || 20)
    },
  },
  {
    method: 'GET', re: /^\/products$/, handler: ({ params }) => {
      const st = getState()
      const rows = st.products.map((p) => ({
        id: p.id, name: p.name, sku: p.sku, fnsKu: null, caseQty: 1, unit: p.unit,
        width: 0, height: 0, length: 0, weight: 0, status: 'ACTIVE',
        createdAt: fmtDateTime(new Date()), updatedAt: fmtDateTime(new Date()),
      }))
      return pageOf(rows, Number(params.page) || 1, Number(params.pageSize) || 20)
    },
  },

  // ---- 销售订单 ----
  {
    method: 'GET', re: /^\/sales-orders$/, handler: ({ params }) => {
      const st = getState()
      let rows = [...st.orders]
      if (params.status) rows = rows.filter((o) => o.status === params.status)
      if (params.keyword) {
        const kw = String(params.keyword)
        rows = rows.filter((o) => o.orderNo.includes(kw) || o.customerName.includes(kw))
      }
      rows.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
      return pageOf(rows.map(orderResp), Number(params.page) || 1, Number(params.pageSize) || 20)
    },
  },
  {
    method: 'GET', re: /^\/sales-orders\/(\d+)$/, handler: ({ match }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      return orderResp(o)
    },
  },
  {
    method: 'POST', re: /^\/sales-orders$/, handler: ({ body }) => {
      const st = getState()
      const customer = st.customers.find((c) => c.id === Number(body.customerId))
      if (!customer) throw new Error('客户不存在')
      const items = (body.items || []).map((i: any) => {
        const p = st.products.find((x) => x.id === Number(i.productId))
        if (!p) throw new Error(`商品不存在: ${i.productId}`)
        const amount = round2(Number(i.quantity) * Number(i.unitPrice))
        return { productId: p.id, productName: p.name, quantity: Number(i.quantity), unitPrice: round2(i.unitPrice), amount }
      })
      if (!items.length) throw new Error('销售订单至少需要一条明细')
      const order: MockOrder = {
        id: st.orders.length ? Math.max(...st.orders.map((o) => o.id)) + 1 : 1,
        orderNo: nextOrderNo(st),
        customerId: customer.id,
        customerName: customer.name,
        status: 'DRAFT',
        creditDays: Number(body.creditDays) || 0,
        totalAmount: round2(items.reduce((s: number, i: any) => s + i.amount, 0)),
        outboundOrderNo: null,
        shippedAt: null,
        remark: body.remark ?? null,
        items,
        createdAt: fmtDateTime(new Date()),
      }
      st.orders.push(order)
      return orderResp(order)
    },
  },
  {
    method: 'PUT', re: /^\/sales-orders\/(\d+)$/, handler: ({ match, body }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      if (o.status !== 'DRAFT') throw new Error(`当前状态 ${o.status} 不允许编辑订单`)
      if (body.creditDays !== undefined) o.creditDays = Number(body.creditDays) || 0
      if (body.remark !== undefined) o.remark = body.remark
      if (body.items) {
        o.items = body.items.map((i: any) => {
          const p = st.products.find((x) => x.id === Number(i.productId))
          if (!p) throw new Error(`商品不存在: ${i.productId}`)
          return { productId: p.id, productName: p.name, quantity: Number(i.quantity), unitPrice: round2(i.unitPrice), amount: round2(Number(i.quantity) * Number(i.unitPrice)) }
        })
        o.totalAmount = round2(o.items.reduce((s, i) => s + i.amount, 0))
      }
      return orderResp(o)
    },
  },
  {
    method: 'POST', re: /^\/sales-orders\/(\d+)\/confirm$/, handler: ({ match }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      if (o.status !== 'DRAFT') throw new Error(`当前状态 ${o.status} 不允许确认`)
      o.status = 'CONFIRMED'
      return orderResp(o)
    },
  },
  {
    method: 'POST', re: /^\/sales-orders\/(\d+)\/ship$/, handler: ({ match, body }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      if (o.status === 'SHIPPED') throw new Error('该订单已发货,不能重复发货')
      if (o.status !== 'CONFIRMED') throw new Error(`当前状态 ${o.status} 不允许发货`)
      o.status = 'SHIPPED'
      o.shippedAt = fmtDateTime(new Date())
      if (body?.outboundOrderNo) o.outboundOrderNo = body.outboundOrderNo
      generateReceivable(st, o) // 发货才生成应收(幂等)
      return orderResp(o)
    },
  },
  {
    method: 'POST', re: /^\/sales-orders\/(\d+)\/complete$/, handler: ({ match }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      if (o.status !== 'SHIPPED') throw new Error(`当前状态 ${o.status} 不允许完成`)
      o.status = 'COMPLETED'
      return orderResp(o)
    },
  },
  {
    method: 'POST', re: /^\/sales-orders\/(\d+)\/cancel$/, handler: ({ match }) => {
      const st = getState()
      const o = st.orders.find((x) => x.id === Number(match[1]))
      if (!o) throw new Error('销售订单不存在')
      if (!['DRAFT', 'CONFIRMED'].includes(o.status)) throw new Error(`当前状态 ${o.status} 不允许作废`)
      o.status = 'CANCELLED'
      return orderResp(o)
    },
  },

  // ---- 财务:应收 / 账龄 / 收款核销 ----
  {
    method: 'GET', re: /^\/finance\/receivables$/, handler: ({ params }) => {
      const st = getState()
      const today = todayStr()
      let rows = st.entries.filter((e) => e.entryType === 'RECEIVABLE')
      if (params.partnerName) rows = rows.filter((e) => e.partnerName.includes(String(params.partnerName)))
      if (params.status) rows = rows.filter((e) => e.status === params.status)
      if (params.onlyOutstanding) rows = rows.filter((e) => outstandingOf(e) > 0)
      if (params.onlyOverdue) rows = rows.filter((e) => e.dueDate && e.dueDate < today && outstandingOf(e) > 0)
      rows.sort((a, b) => ((a.dueDate || '') < (b.dueDate || '') ? -1 : 1))
      return pageOf(rows.map(entryResp), Number(params.page) || 1, Number(params.pageSize) || 20)
    },
  },
  {
    method: 'GET', re: /^\/finance\/aging$/, handler: () => {
      const st = getState()
      const map = new Map<string, any>()
      for (const e of st.entries.filter((x) => x.entryType === 'RECEIVABLE')) {
        const out = outstandingOf(e)
        if (out <= 0) continue
        const row = map.get(e.partnerName) || {
          partnerName: e.partnerName, receivableTotal: 0, settledTotal: 0, balance: 0,
          notDue: 0, days1to30: 0, days31to60: 0, days60plus: 0,
        }
        row.receivableTotal = round2(row.receivableTotal + e.amount)
        row.settledTotal = round2(row.settledTotal + e.settledAmount)
        row.balance = round2(row.balance + out)
        const b = agingBucket(e.dueDate)
        row[b] = round2(row[b] + out)
        map.set(e.partnerName, row)
      }
      return [...map.values()].sort((a, b) => b.balance - a.balance)
    },
  },
  {
    method: 'POST', re: /^\/finance\/receipts$/, handler: ({ body }) => entryResp(applyReceipt(getState(), {
      partnerName: body.partnerName,
      amount: Number(body.amount),
      occurredDate: body.occurredDate,
      remark: body.remark,
      allocations: body.allocations,
    })),
  },
  {
    method: 'POST', re: /^\/finance\/receipts\/(\d+)\/allocate$/, handler: ({ match, body }) =>
      entryResp(allocateReceipt(getState(), Number(match[1]), body?.allocations || [])),
  },

  // ---- 经营驾驶舱 ----
  {
    method: 'GET', re: /^\/executive\/summary$/, handler: () => {
      const st = getState()
      const today = todayStr()
      const ars = st.entries.filter((e) => e.entryType === 'RECEIVABLE')
      const receivableTotal = round2(ars.reduce((s, e) => s + e.amount, 0))
      const receivedTotal = round2(ars.reduce((s, e) => s + e.settledAmount, 0))
      const outstandingTotal = round2(ars.reduce((s, e) => s + outstandingOf(e), 0))
      const overdueTotal = round2(ars.filter((e) => e.dueDate && e.dueDate < today)
        .reduce((s, e) => s + outstandingOf(e), 0))
      const validOrders = st.orders.filter((o) => o.status !== 'CANCELLED')
      return {
        receivableTotal, receivedTotal, outstandingTotal, overdueTotal,
        orderCount: validOrders.length,
        orderAmount: round2(validOrders.reduce((s, o) => s + o.totalAmount, 0)),
      }
    },
  },
  {
    method: 'GET', re: /^\/executive\/receivable-top$/, handler: ({ params }) => {
      const st = getState()
      const today = todayStr()
      const map = new Map<string, { partnerName: string; balance: number; overdue: number }>()
      for (const e of st.entries.filter((x) => x.entryType === 'RECEIVABLE')) {
        const out = outstandingOf(e)
        if (out <= 0) continue
        const row = map.get(e.partnerName) || { partnerName: e.partnerName, balance: 0, overdue: 0 }
        row.balance = round2(row.balance + out)
        if (e.dueDate && e.dueDate < today) row.overdue = round2(row.overdue + out)
        map.set(e.partnerName, row)
      }
      return [...map.values()].sort((a, b) => b.balance - a.balance).slice(0, Number(params.limit) || 5)
    },
  },
  {
    method: 'GET', re: /^\/executive\/aging-distribution$/, handler: () => {
      const st = getState()
      const dist = { notDue: 0, days1to30: 0, days31to60: 0, days60plus: 0 }
      for (const e of st.entries.filter((x) => x.entryType === 'RECEIVABLE')) {
        const out = outstandingOf(e)
        if (out <= 0) continue
        const b = agingBucket(e.dueDate) as keyof typeof dist
        dist[b] = round2(dist[b] + out)
      }
      return dist
    },
  },
  {
    method: 'GET', re: /^\/executive\/trends$/, handler: ({ params }) => {
      const st = getState()
      const days = Number(params.days) || 30
      const today = todayStr()
      const orderByDay = new Map<string, number>()
      for (const o of st.orders) {
        if (o.status === 'CANCELLED') continue
        const d = o.createdAt.slice(0, 10)
        orderByDay.set(d, round2((orderByDay.get(d) || 0) + o.totalAmount))
      }
      const receiptByDay = new Map<string, number>()
      for (const e of st.entries.filter((x) => x.entryType === 'RECEIPT')) {
        receiptByDay.set(e.occurredDate, round2((receiptByDay.get(e.occurredDate) || 0) + e.amount))
      }
      const series: Array<{ date: string; orderAmount: number; receiptAmount: number }> = []
      for (let i = days - 1; i >= 0; i--) {
        const date = addDays(today, -i)
        series.push({
          date,
          orderAmount: round2(orderByDay.get(date) || 0),
          receiptAmount: round2(receiptByDay.get(date) || 0),
        })
      }
      return series
    },
  },
]

// ============ 兜底(未覆盖接口返回空结果,保证旧页面不崩) ============

const EMPTY_PAGE_PATHS = [
  /^\/users$/, /^\/inventory$/, /^\/inventory\/flows$/, /^\/inventory\/batches$/,
  /^\/inbound-orders$/, /^\/outbound-orders$/, /^\/returns$/, /^\/waves$/,
  /^\/waves\/picking-orders$/, /^\/transfers$/, /^\/adjustments$/, /^\/counts$/,
]
const EMPTY_ARRAY_PATHS = [/^\/warehouses$/, /^\/zones$/, /^\/locations$/]

const fallbackHandler = ({ method, path, params }: Ctx) => {
  if (method === 'GET' && path === '/dashboard/summary') {
    return {
      todayInboundCount: 0, todayOutboundCount: 0, pendingInboundCount: 0, pendingOutboundCount: 0,
      totalInventoryQty: 0, lowStockProductCount: 0, activeProductCount: 0, activeCustomerCount: 0,
    }
  }
  if (method === 'GET' && EMPTY_PAGE_PATHS.some((re) => re.test(path))) {
    return pageOf([], Number(params.page) || 1, Number(params.pageSize) || 20)
  }
  if (method === 'GET' && EMPTY_ARRAY_PATHS.some((re) => re.test(path))) return []
  return null
}

// ============ 适配器 ============

export const mockAdapter: AxiosAdapter = async (config) => {
  await delay(120) // 轻微延迟,更接近真实请求

  const rawUrl = config.url || ''
  const path = rawUrl.replace(/^https?:\/\/[^/]+/, '').replace(/^\/api/, '').split('?')[0] || '/'
  const method = (config.method || 'get').toUpperCase()
  const params = (config.params || {}) as Record<string, any>
  let body: any
  if (config.data) {
    body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
  }

  for (const route of routes) {
    if (route.method !== method) continue
    const match = path.match(route.re)
    if (!match) continue
    try {
      const data = route.handler({ config, method, path, params, body, match })
      return makeResponse(config, data)
    } catch (e: any) {
      throw new MockHttpError(config, e.message || '操作失败', 400)
    }
  }

  try {
    return makeResponse(config, fallbackHandler({ config, method, path, params, body, match: [] as any }))
  } catch (e: any) {
    throw new MockHttpError(config, e.message || '操作失败', 400)
  }
}
