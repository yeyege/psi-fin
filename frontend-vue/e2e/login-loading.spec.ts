import { test, expect, type Route } from '@playwright/test'

/**
 * 登录页「唤醒进度」设计回归（对应演示环境 Serverless 冷启动 20–30s 的体验问题）
 *
 * 全部用 page.route 打桩 /api/*，不依赖真实后端与数据库：
 * - 冷启动等待：延迟响应 → 断言阶段文案、进度轨、按钮禁用
 * - 凭据错误：401 → 断言提示是「账号或密码错误」而非服务异常
 * - 服务不可达：abort → 断言常驻错误块 + 重试入口（旧实现会误报成密码错误）
 */

const HEALTH = '**/api/health'
const LOGIN = '**/api/auth/login'

const loginPayload = {
  code: 200,
  message: '登录成功',
  data: {
    token: 'e2e-fake-token',
    user: { id: 1, username: 'admin', role: 'admin', status: 'ACTIVE', createdAt: '2026-01-01T00:00:00' },
  },
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

const fillAndSubmit = async (page: import('@playwright/test').Page) => {
  await page.getByPlaceholder('请输入企业分配的账号').fill('admin')
  await page.getByPlaceholder('请输入登录密码').fill('admin123')
  await page.getByRole('button', { name: '登 录' }).click()
}

test.beforeEach(async ({ page }) => {
  // 预热探针默认立即就绪，避免各用例被挂起的 /health 干扰
  await page.route(HEALTH, (route: Route) =>
    route.fulfill({ json: { code: 200, message: 'ok', data: { status: 'up' } } }))
})

test('预热成功后顶部状态灯为「系统正常」', async ({ page }) => {
  await page.goto('/#/login')
  await expect(page.locator('.nav-status')).toContainText('系统正常')
})

test('预热挂起时顶部状态灯为「正在唤醒服务」', async ({ page }) => {
  await page.route(HEALTH, async (route: Route) => {
    await delay(5_000)
    await route.fulfill({ json: { code: 200, message: 'ok', data: { status: 'up' } } })
  })
  await page.goto('/#/login')
  await expect(page.locator('.nav-status')).toContainText('正在唤醒服务')
})

test('前 1.2 秒只有按钮转圈，等得不对劲时才出现唤醒解释块', async ({ page }) => {
  await page.route(LOGIN, async (route: Route) => {
    await delay(4_000)
    await route.fulfill({ json: loginPayload })
  })
  await page.goto('/#/login')
  await fillAndSubmit(page)

  // 常规耗时内不打扰：无解释块，仅按钮进入 loading
  await expect(page.getByRole('button', { name: '正在验证身份…' })).toBeDisabled()
  await expect(page.locator('.login-progress')).toHaveCount(0)

  // 超过 WAKE_HINT_AFTER_MS 后：解释「为什么在等」与「还要多久」
  await expect(page.locator('.progress-title')).toHaveText('首次访问正在拉起演示环境，通常 20 秒内完成', { timeout: 5_000 })
  await expect(page.locator('.progress-note')).toContainText('Serverless')
  await expect(page.locator('.progress-meta')).toContainText(/已等待 \d+ 秒 · 通常 20 秒内完成/)
  await expect(page.locator('.progress-rail')).toBeVisible()
  await expect(page.getByRole('button', { name: '正在唤醒服务…' })).toBeDisabled()

  // 不断言 URL：假 token 会让 Dashboard 的真实接口返回 401，被全局拦截器踢回 /login；
  // 这里只关心登录流程本身是否成功结束（toast + 进度块收起）
  await expect(page.locator('.el-message')).toContainText('登录成功')
  await expect(page.locator('.login-progress')).toHaveCount(0)
})

test('凭据错误提示为账号或密码问题，不混淆成服务故障', async ({ page }) => {
  await page.route(LOGIN, (route: Route) =>
    route.fulfill({ status: 401, json: { code: 401, message: '用户名或密码错误', detail: '用户名或密码错误' } }))
  await page.goto('/#/login')
  await fillAndSubmit(page)

  await expect(page.locator('.progress-title')).toContainText('用户名或密码错误')
  await expect(page.locator('.progress-rail')).toHaveCount(0)
  await expect(page.locator('.progress-retry')).toHaveCount(0)
  // 服务已响应 → 状态灯回到正常
  await expect(page.locator('.nav-status')).toContainText('系统正常')
})

test('服务不可达时给出常驻提示与重试入口，输入内容被保留', async ({ page }) => {
  await page.route(LOGIN, (route: Route) => route.abort('failed'))
  await page.goto('/#/login')
  await fillAndSubmit(page)

  await expect(page.locator('.progress-title')).toContainText('网络连接异常')
  const retry = page.getByRole('button', { name: '重试' })
  await expect(retry).toBeVisible()
  await expect(page.getByPlaceholder('请输入企业分配的账号')).toHaveValue('admin')

  // 服务恢复后点重试即可登录，无需重填
  await page.unroute(LOGIN)
  await page.route(LOGIN, (route: Route) => route.fulfill({ json: loginPayload }))
  await retry.click()
  await expect(page.locator('.el-message')).toContainText('登录成功')
})

test('修改输入后旧的失败提示自动消失', async ({ page }) => {
  await page.route(LOGIN, (route: Route) => route.abort('failed'))
  await page.goto('/#/login')
  await fillAndSubmit(page)
  await expect(page.locator('.progress-title')).toContainText('网络连接异常')

  await page.getByPlaceholder('请输入登录密码').fill('admin1234')
  await expect(page.locator('.login-progress')).toHaveCount(0)
})
