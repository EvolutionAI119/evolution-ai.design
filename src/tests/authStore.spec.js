// 认证 Pinia store 测试：登录/注册写入 JWT、fetchMe 拉取用户、失效清空、退出。
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 模拟 API 层，store 逻辑不依赖真实网络
vi.mock('../api', () => ({
  authAPI: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn()
  }
}))

import { authAPI } from '../api'
import { useAuthStore } from '../stores/auth'

const TOKEN_KEY = 'evoai_token'

const fakeUser = { id: 1, email: 'a@b.com', username: '测试', is_admin: false }
const fakeToken = 'jwt-token-123'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('初始状态', () => {
  it('无本地 token 时未认证', () => {
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
  })

  it('本地已有 token 时自动恢复认证态', () => {
    localStorage.setItem(TOKEN_KEY, 'persisted-jwt')
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.token).toBe('persisted-jwt')
  })
})

describe('login / register', () => {
  it('login 成功：保存 token 与用户信息', async () => {
    authAPI.login.mockResolvedValue({
      data: { access_token: fakeToken, user: fakeUser }
    })
    const auth = useAuthStore()
    const data = await auth.login('a@b.com', 'pass123')

    expect(data.access_token).toBe(fakeToken)
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user).toEqual(fakeUser)
    expect(localStorage.getItem(TOKEN_KEY)).toBe(fakeToken)
  })

  it('register 成功：同样持久化登录态', async () => {
    authAPI.register.mockResolvedValue({
      data: { access_token: fakeToken, user: fakeUser }
    })
    const auth = useAuthStore()
    await auth.register('a@b.com', '测试', 'pass123')

    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem(TOKEN_KEY)).toBe(fakeToken)
  })
})

describe('fetchMe', () => {
  it('无 token 时直接返回 null，不发请求', async () => {
    const auth = useAuthStore()
    const result = await auth.fetchMe()
    expect(result).toBeNull()
    expect(authAPI.me).not.toHaveBeenCalled()
  })

  it('有 token 时拉取并写入用户信息', async () => {
    authAPI.me.mockResolvedValue({ data: fakeUser })
    const auth = useAuthStore()
    auth.setToken(fakeToken)

    const result = await auth.fetchMe()
    expect(result).toEqual(fakeUser)
    expect(auth.user).toEqual(fakeUser)
  })

  it('token 失效（请求失败）：清空登录态并向上抛出', async () => {
    authAPI.me.mockRejectedValue(new Error('401 Unauthorized'))
    const auth = useAuthStore()
    auth.setToken(fakeToken)

    await expect(auth.fetchMe()).rejects.toThrow('401 Unauthorized')
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
  })
})

describe('logout', () => {
  it('退出清除 token、用户与本地存储', async () => {
    authAPI.login.mockResolvedValue({
      data: { access_token: fakeToken, user: fakeUser }
    })
    const auth = useAuthStore()
    await auth.login('a@b.com', 'pass123')

    auth.logout()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.token).toBe('')
    expect(auth.user).toBeNull()
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
  })
})
