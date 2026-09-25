import { type Page } from '@playwright/test'

/**
 * E2E 登录步骤（全局登录校验上线后，所有用例先登录再访问业务页）
 * 默认管理员：admin / admin123（init_admin 启动时自动创建）
 *
 * 定位用 autocomplete 而非 placeholder：登录页是可切换中英文的、带品牌文案的页面，
 * placeholder 会随文案改版（上一版就是改版后静默失效了两个月）；
 * `username` / `current-password` 是输入框声明的 HTML 语义属性，也是浏览器密码管理器依赖的键。
 */
export async function login(page: Page, username = 'admin', password = 'admin123') {
  await page.goto('/#/login')
  await page.locator('input[autocomplete="username"]').fill(username)
  await page.locator('input[autocomplete="current-password"]').fill(password)
  await page.getByRole('button', { name: '登 录' }).click()
  await page.waitForURL(/#\/dashboard/)
}
