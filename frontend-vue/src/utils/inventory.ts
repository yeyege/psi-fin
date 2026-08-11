/**
 * 库存相关纯函数 — 抽离以便单元测试（选做 B）
 *
 * 将「低库存判定」与「前端关键词筛选」从组件中抽离为纯函数，
 * 既便于测试，也便于后续在虚拟滚动等场景复用。
 */
import type { InventoryItem } from '@/api'

/** 低库存阈值（数量低于此值视为低库存，需高亮） */
export const LOW_STOCK_THRESHOLD = 10

/**
 * 判断某条库存是否为低库存
 * @param quantity 库存数量
 * @param threshold 阈值，默认 10
 */
export function isLowStock(quantity: number, threshold: number = LOW_STOCK_THRESHOLD): boolean {
  return typeof quantity === 'number' && quantity < threshold
}

/**
 * 前端关键词筛选：按商品名称或 SKU 模糊匹配
 * （后端已做筛选，此函数用于本地二次过滤 / 虚拟滚动等场景）
 */
export function filterByKeyword(items: InventoryItem[], keyword: string): InventoryItem[] {
  const kw = keyword.trim().toLowerCase()
  if (!kw) return items
  return items.filter(
    (it) =>
      it.productName.toLowerCase().includes(kw) || it.sku.toLowerCase().includes(kw),
  )
}

/**
 * 按仓库 ID 筛选
 */
export function filterByWarehouse(
  items: InventoryItem[],
  warehouseName: string | undefined,
): InventoryItem[] {
  if (!warehouseName) return items
  return items.filter((it) => it.warehouseName === warehouseName)
}

/**
 * 低库存行样式 class（供 el-table :row-class-name 使用）
 */
export function lowStockRowClass({ row }: { row: InventoryItem }): string {
  return isLowStock(row.quantity) ? 'low-stock-row' : ''
}
