import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：统一提取 data
api.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const msg = error.response?.data?.message || error.message || '网络错误'
    console.error('API Error:', msg)
    return Promise.reject(error)
  }
)

export default api
