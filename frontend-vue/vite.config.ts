/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  // GitHub Pages 项目站点挂载在 /wms/ 子路径下，资源必须用相对/子路径 base
  base: '/wms/',
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
