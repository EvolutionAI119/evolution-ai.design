// 用户认证状态：JWT 持久化 + 当前用户信息
import { defineStore } from 'pinia'
import { authAPI } from '../api'

const TOKEN_KEY = 'evoai_token'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: null,
    loading: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    // 当前角色：未登录为 guest；后端返回的 role 为权威字段
    role: (state) => state.user?.role || 'guest',
    // 管理员（admin / superadmin），兼容历史 is_admin 标记
    isAdmin: (state) => {
      const role = state.user?.role
      return role === 'admin' || role === 'superadmin' ||
        (!role && !!state.user?.is_admin)
    },
    isSuperadmin: (state) => state.user?.role === 'superadmin'
  },

  actions: {
    setToken(token) {
      this.token = token
      if (token) {
        localStorage.setItem(TOKEN_KEY, token)
      } else {
        localStorage.removeItem(TOKEN_KEY)
      }
    },

    async login(email, password) {
      this.loading = true
      try {
        const { data } = await authAPI.login({ email, password })
        this.setToken(data.access_token)
        this.user = data.user
        return data
      } finally {
        this.loading = false
      }
    },

    async register(email, username, password) {
      this.loading = true
      try {
        const { data } = await authAPI.register({ email, username, password })
        this.setToken(data.access_token)
        this.user = data.user
        return data
      } finally {
        this.loading = false
      }
    },

    async fetchMe() {
      if (!this.token) {
        this.user = null
        return null
      }
      try {
        const { data } = await authAPI.me()
        this.user = data
        return data
      } catch (e) {
        // 令牌失效：清空并触发重新登录
        this.setToken('')
        this.user = null
        throw e
      }
    },

    logout() {
      this.setToken('')
      this.user = null
    }
  }
})
