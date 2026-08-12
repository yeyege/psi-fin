import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E 配置（只测核心正向流程）
 * webServer 自动拉起：后端 FastAPI(8000) + 前端 Vite(5173，代理 /api→8000)
 * 本地已有服务在跑时（reuseExistingServer）直接复用，避免端口冲突。
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      // channel: 'chromium' 使用完整 Chrome for Testing（headless 也走完整内核，无需 headless-shell）
      use: { ...devices['Desktop Chrome'], channel: 'chromium' },
    },
  ],
  webServer: [
    {
      command: 'uv run uvicorn app.main:app --port 8000',
      cwd: '../backend-python',
      url: 'http://localhost:8000/docs',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      cwd: '.',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
