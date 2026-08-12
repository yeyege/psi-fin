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
      use: {
        ...devices['Desktop Chrome'],
        // 使用系统已安装的 Chrome，避免下载 Playwright 自带浏览器（国内网络常下载失败）
        channel: 'chrome',
        // 沙箱/CI 环境禁用 GPU 与 shader cache，避免访问 NVIDIA/Intel 缓存目录受限
        launchOptions: {
          args: ['--no-sandbox', '--disable-gpu', '--disable-shader-cache'],
        },
      },
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
