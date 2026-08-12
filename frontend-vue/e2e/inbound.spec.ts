import { test, expect } from '@playwright/test'
import { login } from './helpers'

/**
 * E2E 核心正向流程：入库
 * 打开 /inbound → 新建入库单 → 填供应商 / 选商品 / 选库位 → 提交
 * → 断言页面出现「创建成功」提示与单号 IN-xxxx
 * 种子数据（init_data.py 启动时自动写入）：SKU-001 蓝牙耳机 Pro、库位 A-01-01
 */
test('入库正向流程：创建入库单并提示成功', async ({ page }) => {
  await login(page) // 全局登录校验：先登录再进入业务页
  await page.goto('/#/inbound')

  // 页面加载：新建按钮可见（等待商品/库位下拉数据就绪）
  const createBtn = page.getByRole('button', { name: '新建入库单' })
  await expect(createBtn).toBeVisible()
  await createBtn.click()

  // 1. 填写供应商（accessible name 由 el-form-item label 提供）
  await page.getByRole('textbox', { name: '供应商' }).fill('Playwright E2E 供应商')

  // 2. 选择商品（种子数据 SKU-001）—— el-select 通过 .el-select__wrapper 展开下拉
  await page.locator('.el-dialog .el-select__wrapper').first().click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'SKU-001' }).click()

  // 3. 选择目标库位（种子数据 A-01-01）
  await page.locator('.el-dialog .el-select__wrapper').nth(1).click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'A-01-01' }).click()

  // 4. 提交创建
  await page.getByRole('button', { name: '创建' }).click()

  // 5. 断言：出现「成功」提示且包含单号
  const success = page.locator('.el-message--success')
  await expect(success).toBeVisible({ timeout: 10_000 })
  await expect(success).toContainText('创建成功')
  await expect(success).toContainText('IN-')
})
