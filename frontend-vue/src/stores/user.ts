import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout, getMe, type UserInfo } from '@/api'

const TOKEN_KEY = 'wms_token'
const USER_KEY = 'wms_user'

interface UserState {
  token: string
  user: UserInfo | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username: string, password: string) {
      const res = await apiLogin({ username, password })
      this.token = res.data.token
      this.user = res.data.user
      localStorage.setItem(TOKEN_KEY, this.token)
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      return this.user
    },
    async fetchMe() {
      const res = await getMe()
      this.user = res.data
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      return this.user
    },
    async logout() {
      try {
        await apiLogout()
      } catch {
        // 登出接口失败不阻塞本地清理
      }
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
