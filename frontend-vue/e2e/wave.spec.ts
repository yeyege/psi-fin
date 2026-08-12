import { test, expect } from '@playwright/test'

/**
 * E2E 核心正向流程：波次拣货（含前置：创建出库单）
 * 1. 打开 /outbound → 新建出库单（客户 / 商品 SKU-001 / 库位 A-01-01）→ 创建成功
 * 2. 打开 /waves → 生成波次 → 勾选刚创建的出库单 → 生成成功，断言 WV-xxxx 单号
 * 种子数据（init_data.py 启动时自动写入）：商品 SKU-001、库位 A-01-01
 */
test('波次正向流程：创建出库单 → 生成波次并提示成功', async ({ page }) => {
  // ===== 步骤 1：创建一张 PENDING 出库单 =====
  await page.goto('/#/outbound')

  const createBtn = page.getByRole('button', { name: '新建出库单' })
  await expect(createBtn).toBeVisible()
  await createBtn.click()

  await page.getByRole('textbox', { name: '客户' }).fill('E2E 波次客户')

  await page.locator('.el-dialog .el-select__wrapper').first().click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'SKU-001' }).click()
  await page.locator('.el-dialog .el-select__wrapper').nth(1).click()
  await page.locator('.el-select-dropdown__item:visible', { hasText: 'A-01-01' }).click()

  await page.getByRole('button', { name: '创建' }).click()

  const outSuccess = page.locator('.el-message--success')
  await expect(outSuccess).toBeVisible({ timeout: 10_000 })
  await expect(outSuccess).toContainText('创建成功')
  await expect(outSuccess).toContainText('OUT-')

  // ===== 步骤 2：生成波次 =====
  await page.goto('/#/waves')

  const waveBtn = page.getByRole('button', { name: '生成波次' })
  await expect(waveBtn).toBeVisible()
  await waveBtn.click()

  // 勾选列表中的第一张待拣出库单
  const firstCheckbox = page.locator('.el-dialog .el-checkbox').first()
  await expect(firstCheckbox).toBeVisible()
  await firstCheckbox.click()

  // 提交生成波次
  await page.locator('.el-dialog').getByRole('button', { name: '生成波次' }).click()

  // 断言最新一条成功提示（前一条出库单提示仍在淡出，取 last）
  const success = page.locator('.el-message--success').last()
  await expect(success).toBeVisible({ timeout: 10_000 })
  await expect(success).toContainText('波次')
  await expect(success).toContainText('生成成功')
  await expect(success).toContainText('WV-')
})
