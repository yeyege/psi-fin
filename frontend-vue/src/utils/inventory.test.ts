/**
 * 库存筛选逻辑单元测试 — 选做 B（前端：至少 2 个用例）
 */
import { describe, it, expect } from 'vitest'
import {
  isLowStock,
  filterByKeyword,
  filterByWarehouse,
  lowStockRowClass,
  LOW_STOCK_THRESHOLD,
} from './inventory'
import type { InventoryItem } from '@/api'

const makeItem = (over: Partial<InventoryItem> = {}): InventoryItem => ({
  productId: 1,
  productName: '蓝牙耳机',
  sku: 'SKU-001',
  locationCode: 'A-01',
  warehouseName: '广州主仓',
  quantity: 100,
  updatedAt: '2026-08-11T10:00:00',
  ...over,
})

describe('isLowStock', () => {
  it('数量小于阈值判定为低库存', () => {
    expect(isLowStock(0)).toBe(true)
    expect(isLowStock(9)).toBe(true)
  })

  it('数量大于等于阈值判定为非低库存（边界值 10 不算低库存）', () => {
    expect(isLowStock(10)).toBe(false)
    expect(isLowStock(100)).toBe(false)
  })

  it('支持自定义阈值', () => {
    expect(isLowStock(20, 30)).toBe(true)
    expect(isLowStock(30, 30)).toBe(false)
  })

  it('阈值为常量 10', () => {
    expect(LOW_STOCK_THRESHOLD).toBe(10)
  })
})

describe('filterByKeyword', () => {
  const items = [
    makeItem({ productName: '蓝牙耳机', sku: 'SKU-001' }),
    makeItem({ productName: 'Type-C 数据线', sku: 'SKU-002', productId: 2 }),
    makeItem({ productName: '手机壳', sku: 'BT-003', productId: 3 }),
  ]

  it('按商品名称模糊匹配', () => {
    const r = filterByKeyword(items, '耳机')
    expect(r).toHaveLength(1)
    expect(r[0].productName).toBe('蓝牙耳机')
  })

  it('按 SKU 模糊匹配（大小写不敏感）', () => {
    const r = filterByKeyword(items, 'sku-002')
    expect(r).toHaveLength(1)
    expect(r[0].sku).toBe('SKU-002')
  })

  it('空关键词返回全部', () => {
    expect(filterByKeyword(items, '')).toHaveLength(3)
    expect(filterByKeyword(items, '   ')).toHaveLength(3)
  })

  it('无匹配返回空数组', () => {
    expect(filterByKeyword(items, '不存在的商品')).toHaveLength(0)
  })
})

describe('filterByWarehouse', () => {
  const items = [
    makeItem({ warehouseName: '广州主仓', productId: 1 }),
    makeItem({ warehouseName: '深圳保税仓', productId: 2 }),
    makeItem({ warehouseName: '广州主仓', productId: 3 }),
  ]

  it('按仓库名筛选', () => {
    const r = filterByWarehouse(items, '广州主仓')
    expect(r).toHaveLength(2)
    expect(r.every((i) => i.warehouseName === '广州主仓')).toBe(true)
  })

  it('未指定仓库返回全部', () => {
    expect(filterByWarehouse(items, undefined)).toHaveLength(3)
  })
})

describe('lowStockRowClass', () => {
  it('低库存行返回 low-stock-row class', () => {
    expect(lowStockRowClass({ row: makeItem({ quantity: 5 }) })).toBe('low-stock-row')
  })

  it('正常库存行返回空字符串', () => {
    expect(lowStockRowClass({ row: makeItem({ quantity: 50 }) })).toBe('')
  })
})
