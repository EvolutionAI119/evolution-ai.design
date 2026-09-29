// 认证 Pinia store 测试：登录/注册写入 JWT、fetchMe 拉取用户、失效清空、退出。
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 模拟 API 层，store 逻辑不依赖真实网络
vi.mock('../api', () => ({
  authAPI: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn()
  },
  setApiToken: vi.fn()
}))

import { authAPI } from '../api'
import { useAuthStore } from '../stores/auth'

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

  it('不读取任何持久化凭据：localStorage 残留同名键也不恢复登录态', () => {
    localStorage.setItem('evoai_token', 'stale-jwt')
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.token).toBe('')
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
    // 登录态仅存内存，不写入 localStorage
    expect(localStorage.getItem('evoai_token')).toBeNull()
  })

  it('register 成功：登录态写入内存且不持久化', async () => {
    authAPI.register.mockResolvedValue({
      data: { access_token: fakeToken, user: fakeUser }
    })
    const auth = useAuthStore()
    await auth.register('a@b.com', '测试', 'pass123')

    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem('evoai_token')).toBeNull()
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
    expect(localStorage.getItem('evoai_token')).toBeNull()
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
    expect(localStorage.getItem('evoai_token')).toBeNull()
  })
})

describe('分级角色 getters', () => {
  const loginWith = async (user) => {
    authAPI.login.mockResolvedValue({
      data: { access_token: fakeToken, user }
    })
    const auth = useAuthStore()
    await auth.login('a@b.com', 'pass123')
    return auth
  }

  it('游客（未登录）：role=guest，非管理员', () => {
    const auth = useAuthStore()
    expect(auth.role).toBe('guest')
    expect(auth.isAdmin).toBe(false)
    expect(auth.isSuperadmin).toBe(false)
  })

  it('普通用户：role=user，非管理员', async () => {
    const auth = await loginWith(
      { id: 2, email: 'u@b.com', username: 'U', role: 'user' })
    expect(auth.role).toBe('user')
    expect(auth.isAdmin).toBe(false)
    expect(auth.isSuperadmin).toBe(false)
  })

  it('管理员：role=admin，isAdmin 为 true', async () => {
    const auth = await loginWith(
      { id: 3, email: 'ad@b.com', username: 'AD', role: 'admin' })
    expect(auth.role).toBe('admin')
    expect(auth.isAdmin).toBe(true)
    expect(auth.isSuperadmin).toBe(false)
  })

  it('超级管理员：role=superadmin，isAdmin/isSuperadmin 均为 true', async () => {
    const auth = await loginWith(
      { id: 4, email: 'su@b.com', username: 'SU', role: 'superadmin' })
    expect(auth.role).toBe('superadmin')
    expect(auth.isAdmin).toBe(true)
    expect(auth.isSuperadmin).toBe(true)
  })

  it('兼容旧数据：仅有 is_admin 标记时按管理员对待', async () => {
    const auth = await loginWith(
      { id: 5, email: 'legacy@b.com', username: 'L', is_admin: true })
    expect(auth.isAdmin).toBe(true)
    expect(auth.isSuperadmin).toBe(false)
  })
})
