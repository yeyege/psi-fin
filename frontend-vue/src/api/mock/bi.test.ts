/**
 * BI Mock 数据层单元测试：锁定「可复现性 + 结构契约」
 */
import { describe, it, expect } from 'vitest'
import { generateBiData, mulberry32, hashString, type BiState } from './bi'

const state7d: BiState = { time: { preset: '7d', start: null, end: null }, warehouses: ['all'] }
const state30d: BiState = { time: { preset: '30d', start: null, end: null }, warehouses: ['all'] }
const stateSh: BiState = { time: { preset: '7d', start: null, end: null }, warehouses: ['sh'] }

describe('seeded PRNG', () => {
  it('相同种子序列完全一致', () => {
    const a = mulberry32(1234), b = mulberry32(1234)
    for (let i = 0; i < 50; i++) expect(a()).toBe(b())
  })
  it('hashString 稳定', () => {
    expect(hashString('overview|7d||all')).toBe(hashString('overview|7d||all'))
  })
})

describe('generateBiData 可复现性', () => {
  it('同 state 两次结果深度相等（四视图）', () => {
    expect(generateBiData('overview', state7d)).toEqual(generateBiData('overview', state7d))
    expect(generateBiData('inventory', state7d)).toEqual(generateBiData('inventory', state7d))
    expect(generateBiData('flow', state7d)).toEqual(generateBiData('flow', state7d))
    expect(generateBiData('efficiency', state7d)).toEqual(generateBiData('efficiency', state7d))
  })
  it('不同时间范围产生不同数据', () => {
    expect(generateBiData('overview', state7d)).not.toEqual(generateBiData('overview', state30d))
  })
  it('不同仓库集合产生不同数据', () => {
    expect(generateBiData('overview', state7d)).not.toEqual(generateBiData('overview', stateSh))
  })
})

describe('generateBiData 结构契约与取值范围', () => {
  it('overview：字段齐全 + 趋势长度等于天数', () => {
    const d = generateBiData('overview', state7d)
    expect(d.kpis).toHaveLength(4)
    expect(d.stats).toHaveLength(4)
    expect(d.trend.labels).toHaveLength(7)
    expect(d.trend.inbound).toHaveLength(7)
    expect(d.orderStatus).toHaveLength(4)
    expect(d.alerts.length).toBeLessThanOrEqual(6)
    expect(d.todos.length).toBeGreaterThanOrEqual(5)
  })
  it('inventory：TOP10/库龄5段/ABC 分级合理', () => {
    const d = generateBiData('inventory', state7d)
    expect(d.skuTop10).toHaveLength(10)
    expect(d.ageDistribution).toHaveLength(5)
    expect(d.abc[0].category).toBe('A')
    const cats = new Set(d.abc.map((x) => x.category))
    expect(cats.has('C')).toBe(true)
  })
  it('flow：30 天 + 供应商/客户 TOP10 + 净增减 = 入 - 出', () => {
    const d = generateBiData('flow', state7d)
    expect(d.trend30.labels).toHaveLength(30)
    expect(d.vendors).toHaveLength(10)
    expect(d.customers).toHaveLength(10)
    expect(d.netVal).toBe(d.netIn - d.netOut)
    d.customers.forEach((c) => {
      expect(c.returnRate).toBeGreaterThanOrEqual(0.005)
      expect(c.returnRate).toBeLessThanOrEqual(0.11)
    })
  })
  it('efficiency：人效 50~200 件/天 + 波次完成率 0~100', () => {
    const d = generateBiData('efficiency', state7d)
    expect(d.workerDaily).toHaveLength(8)
    d.workerDaily.forEach((w) => {
      expect(w.days).toHaveLength(7)
      w.days.forEach((q) => {
        expect(q).toBeGreaterThanOrEqual(60)
        expect(q).toBeLessThanOrEqual(200)
      })
    })
    expect(d.wavePct).toBeGreaterThanOrEqual(0)
    expect(d.wavePct).toBeLessThanOrEqual(100)
  })
})
