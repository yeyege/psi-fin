import { type Page } from '@playwright/test'

/**
 * E2E 登录步骤（全局登录校验上线后，所有用例先登录再访问业务页）
 * 默认管理员：admin / admin123（init_admin 启动时自动创建）
 */
export async function login(page: Page, username = 'admin', password = 'admin123') {
  await page.goto('/#/login')
  await page.getByPlaceholder('用户名').fill(username)
  await page.getByPlaceholder('密码').fill(password)
  await page.getByRole('button', { name: '登 录' }).click()
  await page.waitForURL(/#\/dashboard/)
}
