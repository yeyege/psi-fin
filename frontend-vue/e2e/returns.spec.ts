import { test, expect } from '@playwright/test'
import { login } from './helpers'

/**
 * E2E 核心正向流程：退货管理
 * 打开 /returns → 新建退货单 → 选客户 / 选商品 / 选库位（默认转正品 RESELL）→ 提交
 * → 断言出现「创建成功」提示与单号 RT-xxxx
 * 种子数据（init_data.py 启动时自动写入）：客户 CUST-A01 领星科技、商品 SKU-001、库位 A-01-01
 */
test('退货正向流程：创建退货单并提示成功', async ({ page }) => {
  await login(page) // 全局登录校验：先登录再进入业务页
  await page.goto('/#/returns')

  const createBtn = page.getByRole('button', { name: '新建退货单' })
  await expect(createBtn).toBeVisible()
  await createBtn.click()

  // 1. 选择客户（种子 CUST-A01 领星科技）
  await page.locator('.el-dialog .el-select__wrapper').first().click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: '领星科技' }).click()

  // 2. 退货来源默认 FBA（radio-button），保持默认

  // 3. 选择商品（种子 SKU-001）与目标库位（种子 A-01-01）
  await page.locator('.el-dialog .el-select__wrapper').nth(1).click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'SKU-001' }).click()
  await page.locator('.el-dialog .el-select__wrapper').nth(2).click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'A-01-01' }).click()

  // 4. 提交创建
  await page.getByRole('button', { name: '创建' }).click()

  // 5. 断言：出现「创建成功」提示且包含单号（按文本过滤，避免匹配登录欢迎消息）
  const success = page.locator('.el-message--success', { hasText: '创建成功' })
  await expect(success).toBeVisible({ timeout: 10_000 })
  await expect(success).toContainText('RT-')
})
