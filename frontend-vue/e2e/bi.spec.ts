import { test, expect, type Page } from '@playwright/test'
import { login } from './helpers'

/**
 * E2E：BI 工作台（/bi）核心正向流程 + 样式隔离 + Modal 下钻回归
 * - 五面板切换均有图表渲染；经营财务走真实 /api/executive/*
 * - 时间/仓库筛选联动不报错
 * - 预警下钻 Modal 三种关闭方式（×/ESC/遮罩）——回归曾发生的遮罩 .self 失效缺陷
 * - 旧 /executive 重定向 /bi；主站页面无 .bi-scope 串扰
 */

const PANELS = ['数据总览', '库存分析', '出入库分析', '作业效率', '经营财务'] as const

/** 收集 console error / pageerror，测试末尾统一断言为空 */
function watchErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(`console: ${msg.text()}`) })
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
  return errors
}

test('五面板切换 + 筛选联动 + 经营财务真实数据', async ({ page }) => {
  const errors = watchErrors(page)
  await login(page)

  await page.goto('/#/bi')
  await expect(page.locator('.bi-scope .bi-topbar')).toBeVisible()
  await expect(page.locator('.bi-dock button.active')).toHaveText('数据总览')

  for (const panel of PANELS) {
    await page.locator('.bi-dock button', { hasText: panel }).click()
    await expect(page.locator('.bi-dock button.active')).toHaveText(panel)
    // 每个面板至少渲染 2 张 ECharts 画布（具体数量随面板迭代变化，不写死）
    await expect
      .poll(() => page.locator('.bi-panel .bi-chart canvas').count(), { timeout: 10_000 })
      .toBeGreaterThanOrEqual(2)
  }

  // 经营财务：真实接口内容而非降级警示条
  await expect(page.locator('.bi-panel', { hasText: '应收总额' }).first()).toBeVisible()
  await expect(page.locator('.bi-warn', { hasText: '后端不可用' })).toHaveCount(0)

  // 筛选联动：切时间 + 切仓库，图表仍正常渲染
  await page.locator('.bi-dock button', { hasText: '库存分析' }).click()
  const barsBefore = await page.locator('.bi-panel .bi-chart canvas').count()
  await page.locator('.bi-topbar .bi-seg button', { hasText: '近 30 天' }).click()
  await page.locator('.bi-topbar .bi-chip', { hasText: '上海仓' }).click()
  await expect(page.locator('.bi-topbar .bi-chip.active', { hasText: '上海仓' })).toBeVisible()
  await page.locator('.bi-topbar .bi-chip', { hasText: '全部仓库' }).click()
  expect(await page.locator('.bi-panel .bi-chart canvas').count()).toBe(barsBefore)

  expect(errors).toEqual([])
})

test('预警下钻 Modal：打开后 ×/ESC/遮罩 三种方式均可关闭', async ({ page }) => {
  const errors = watchErrors(page)
  await login(page)
  await page.goto('/#/bi')

  const alertRow = page.locator('.bi-alert').first()
  await expect(alertRow).toBeVisible()
  const modal = page.locator('.bi-modal-root')

  // 方式 1：右上角 ×
  await alertRow.click()
  await expect(modal).toBeVisible()
  await expect(modal.locator('.bi-modal-box')).toContainText('SKU 明细')
  await modal.locator('.bi-modal-close').click()
  await expect(modal).toHaveCount(0)

  // 方式 2：ESC
  await alertRow.click()
  await expect(modal).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(modal).toHaveCount(0)

  // 方式 3：点击遮罩（回归 .self 修饰符缺陷：必须点 mask 本身）
  await alertRow.click()
  await expect(modal).toBeVisible()
  await modal.locator('.bi-modal-mask').click({ position: { x: 10, y: 10 } })
  await expect(modal).toHaveCount(0)

  // 反例：点弹窗卡片内部不应关闭
  await alertRow.click()
  await expect(modal).toBeVisible()
  await modal.locator('.bi-modal-box').click({ position: { x: 5, y: 5 } })
  await expect(modal).toBeVisible()
  await page.keyboard.press('Escape')

  expect(errors).toEqual([])
})

test('旧 /executive 重定向 /bi；主站无 .bi-scope 样式串扰', async ({ page }) => {
  const errors = watchErrors(page)
  await login(page)

  await page.goto('/#/executive')
  await expect(page).toHaveURL(/#\/bi$/)
  await expect(page.locator('.bi-scope .bi-topbar')).toBeVisible()

  // 主站业务页：Element 布局正常且无 BI 局部主题残留
  await page.goto('/#/inventory')
  await expect(page.locator('.app-aside')).toBeVisible()
  await expect(page.locator('.bi-scope')).toHaveCount(0)
  await page.goto('/#/dashboard')
  await expect(page.locator('.bi-scope')).toHaveCount(0)

  expect(errors).toEqual([])
})
