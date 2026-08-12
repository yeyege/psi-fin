/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
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
})
