/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  // 读取带 VITE_ 前缀的环境变量（.env.[mode] / 系统环境变量）
  const env = loadEnv(mode, process.cwd(), '')

  return {
    // 部署子路径：默认 '/'；GitHub Pages 由 .env.pages 注入 '/wms/app/'
    base: env.VITE_BASE || '/',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',  // FastAPI 默认端口
          changeOrigin: true,
        },
      },
    },
    test: {
      // e2e 由 Playwright 运行，vitest 只收集 src 下的单元测试
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  }
})
