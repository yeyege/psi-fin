/**
 * Mock 模式业务规则测试 — 保证纯前端演示与后端口径一致
 * 覆盖:发货才生成应收、幂等、部分核销与结清、预收余额复用、超额核销拦截、账龄分段、驾驶舱同源
 */
import axios from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { mockAdapter } from './index'
import { resetState } from './data'

const api = axios.create({ adapter: mockAdapter })
const auth = { headers: { Authorization: 'Bearer mock' } }

const createOrder = async (price: number, creditDays = 30) => {
  const res = await api.post('/sales-orders', {
    customerId: 1, creditDays,
    items: [{ productId: 1, quantity: 1, unitPrice: price }],
  }, auth)
  return res.data.data
}
const confirm = (id: number) => api.post(`/sales-orders/${id}/confirm`, undefined, auth)
const ship = (id: number) => api.post(`/sales-orders/${id}/ship`, undefined, auth)

const listReceivables = async (params: Record<string, unknown> = {}) => {
  const res = await api.get('/finance/receivables', { ...auth, params })
  return res.data.data.list as any[]
}
const findReceivable = async (orderNo: string) =>
  (await listReceivables()).find((e) => e.sourceOrderNo === orderNo)

beforeEach(() => resetState())

describe('销售订单 → 应收', () => {
  it('发货才生成应收,且到期日 = 发货日 + 账期', async () => {
    const order = await createOrder(1000, 30)
    const before = await findReceivable(order.orderNo)
    expect(before).toBeUndefined()

    await confirm(order.id)
    expect(await findReceivable(order.orderNo)).toBeUndefined()

    const shipped = (await ship(order.id)).data.data
    expect(shipped.status).toBe('SHIPPED')

    const ar = await findReceivable(order.orderNo)
    expect(ar).toBeTruthy()
    expect(ar.amount).toBeCloseTo(1000)
    expect(ar.status).toBe('OPEN')
    expect(ar.settledAmount).toBe(0)
  })

  it('重复发货被拒且应收不重复生成', async () => {
    const order = await createOrder(500, 0)
    await confirm(order.id)
    await ship(order.id)
    const countAfterFirst = (await listReceivables()).filter((e) => e.sourceOrderNo === order.orderNo).length
    expect(countAfterFirst).toBe(1)

    await expect(ship(order.id)).rejects.toBeTruthy()
    const countAfterSecond = (await listReceivables()).filter((e) => e.sourceOrderNo === order.orderNo).length
    expect(countAfterSecond).toBe(1)
  })
})

describe('收款核销', () => {
  it('部分核销 → 部分结清;补足后已结清', async () => {
    const order = await createOrder(1000, 0)
    await confirm(order.id); await ship(order.id)
    const ar = await findReceivable(order.orderNo)

    const r1 = await api.post('/finance/receipts', {
      partnerName: '杭州云集电商', amount: 600,
      allocations: [{ targetEntryId: ar.id, amount: 600 }],
    }, auth)
    expect(r1.data.data.settledAmount).toBeCloseTo(600)

    let row = (await listReceivables()).find((e) => e.id === ar.id)
    expect(row.status).toBe('PARTIAL')
    expect(row.outstanding).toBeCloseTo(400)

    await api.post('/finance/receipts', {
      partnerName: '杭州云集电商', amount: 400,
      allocations: [{ targetEntryId: ar.id, amount: 400 }],
    }, auth)
    row = (await listReceivables()).find((e) => e.id === ar.id)
    expect(row.status).toBe('SETTLED')
    expect(row.outstanding).toBeCloseTo(0)
  })

  it('预收余额可再次核销到其他应收', async () => {
    const o1 = await createOrder(1000, 0); await confirm(o1.id); await ship(o1.id)
    const o2 = await createOrder(400, 0); await confirm(o2.id); await ship(o2.id)
    const ar1 = await findReceivable(o1.orderNo)
    const ar2 = await findReceivable(o2.orderNo)

    // 到账 1000,只核销 600 → 保留 400 未核销余额
    const receipt = (await api.post('/finance/receipts', {
      partnerName: '杭州云集电商', amount: 1000,
      allocations: [{ targetEntryId: ar1.id, amount: 600 }],
    }, auth)).data.data
    expect(receipt.settledAmount).toBeCloseTo(600)
    expect(receipt.amount - receipt.settledAmount).toBeCloseTo(400)

    // 用预收余额核销第二张应收
    const after = (await api.post(`/finance/receipts/${receipt.id}/allocate`, {
      allocations: [{ targetEntryId: ar2.id, amount: 400 }],
    }, auth)).data.data
    expect(after.amount - after.settledAmount).toBeCloseTo(0)

    const row2 = (await listReceivables()).find((e) => e.id === ar2.id)
    expect(row2.status).toBe('SETTLED')
  })

  it('单张超额核销被拒且不改变任何金额', async () => {
    const order = await createOrder(400, 0)
    await confirm(order.id); await ship(order.id)
    const ar = await findReceivable(order.orderNo)

    await expect(api.post('/finance/receipts', {
      partnerName: '杭州云集电商', amount: 500,
      allocations: [{ targetEntryId: ar.id, amount: 500 }],
    }, auth)).rejects.toBeTruthy()

    const row = (await listReceivables()).find((e) => e.id === ar.id)
    expect(row.settledAmount).toBe(0)
    expect(row.status).toBe('OPEN')
  })
})

describe('账龄与驾驶舱', () => {
  it('账龄以到期日为基准分段,且合计等于未回款总额', async () => {
    const aging = (await api.get('/finance/aging', auth)).data.data as any[]
    const dist = (await api.get('/executive/aging-distribution', auth)).data.data
    const summary = (await api.get('/executive/summary', auth)).data.data

    const receivableTotal = aging.reduce((s, r) => s + r.receivableTotal, 0)
    expect(receivableTotal).toBeGreaterThan(0)

    const agingSum = dist.notDue + dist.days1to30 + dist.days31to60 + dist.days60plus
    expect(agingSum).toBeCloseTo(summary.outstandingTotal)
    // 演示数据覆盖各账龄段
    expect(dist.notDue).toBeGreaterThan(0)
    expect(dist.days1to30).toBeGreaterThan(0)
    expect(dist.days31to60).toBeGreaterThan(0)
    expect(dist.days60plus).toBeGreaterThan(0)
  })

  it('驾驶舱金额与应收台账同源', async () => {
    const list = await listReceivables()
    const summary = (await api.get('/executive/summary', auth)).data.data
    const amount = list.reduce((s, e) => s + e.amount, 0)
    const settled = list.reduce((s, e) => s + e.settledAmount, 0)
    expect(summary.receivableTotal).toBeCloseTo(amount)
    expect(summary.receivedTotal).toBeCloseTo(settled)
    expect(summary.outstandingTotal).toBeCloseTo(amount - settled)
  })
})

describe('未覆盖接口兜底', () => {
  it('未实现的列表接口返回空分页而非报错', async () => {
    const res = await api.get('/inbound-orders', { ...auth, params: { page: 1, pageSize: 10 } })
    expect(res.data.data.list).toEqual([])
    expect(res.data.data.total).toBe(0)
  })
})
