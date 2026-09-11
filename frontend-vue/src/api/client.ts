import axios from 'axios'
import { mockAdapter } from './mock'

const api = axios.create({
  // 真实后端地址可配置：默认走 `/api`（dev 由 Vite 代理；生产由 nginx 反代）
  // 未来后端上云时，构建注入 VITE_API_BASE=https://<后端域名>/api 即可
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// 纯前端演示模式：开启后所有 /api 请求由浏览器内 Mock 实现响应，不发起真实网络请求
// 由 .env.pages 的 VITE_USE_MOCK=true 在构建时注入
if (import.meta.env.VITE_USE_MOCK === 'true') {
  api.defaults.adapter = mockAdapter
}

// 请求拦截器：自动附加登录 token（Authorization: Bearer <token>）
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wms_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一提取 data；401 时清登录态并跳转登录页
api.interceptors.response.use(
  (res) => res.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('wms_token')
      localStorage.removeItem('wms_user')
      if (window.location.hash !== '#/login') {
        window.location.hash = '#/login'
      }
    }
    const msg = error.response?.data?.message || error.message || '网络错误'
    console.error('API Error:', msg)
    return Promise.reject(error)
  }
)

export default api
