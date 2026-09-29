// 路由守卫测试：分级权限的访问控制（游客 / 普通用户 / 管理员 / 超级管理员）
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 视图组件用桩替代（render 函数，避免依赖运行时模板编译器与重型依赖）
vi.mock('../views/Dashboard.vue', () => ({ default: { name: 'Dashboard', render: () => null } }))
vi.mock('../views/Login.vue', () => ({ default: { name: 'Login', render: () => null } }))
vi.mock('../views/Admin.vue', () => ({ default: { name: 'Admin', render: () => null } }))
// 网络层与全局消息不真正执行
vi.mock('../api', () => ({
  authAPI: { login: vi.fn(), register: vi.fn(), me: vi.fn() },
  setApiToken: vi.fn()
}))
vi.mock('element-plus', () => ({ ElMessage: { warning: vi.fn() } }))

import router from '../router'
import { useAuthStore } from '../stores/auth'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('路由守卫：游客（未登录）', () => {
  it('访问 /admin 重定向到登录页并携带 redirect', async () => {
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query.redirect).toBe('/admin')
  })

  it('访问 /account 重定向到登录页', async () => {
    await router.push('/account')
    expect(router.currentRoute.value.name).toBe('Login')
  })

  it('可自由访问首页 Dashboard', async () => {
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('Dashboard')
  })
})

describe('路由守卫：已登录用户', () => {
  it('普通用户访问 /admin 被弹回 Dashboard', async () => {
    const auth = useAuthStore()
    auth.setToken('jwt-user')
    auth.user = { id: 1, email: 'u@b.com', role: 'user' }
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Dashboard')
  })

  it('管理员可进入 /admin', async () => {
    const auth = useAuthStore()
    auth.setToken('jwt-admin')
    auth.user = { id: 2, email: 'a@b.com', role: 'admin' }
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('超级管理员可进入 /admin', async () => {
    const auth = useAuthStore()
    auth.setToken('jwt-super')
    auth.user = { id: 3, email: 's@b.com', role: 'superadmin' }
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Admin')
  })

  it('token 失效时访问 /admin 回登录页', async () => {
    const auth = useAuthStore()
    auth.setToken('jwt-expired')
    // 直接让 fetchMe 抛错，验证守卫 catch 后重定向到登录页
    auth.fetchMe = vi.fn().mockRejectedValue(new Error('401 Unauthorized'))
    // 上一个用例已停留在 /admin，需先离开再进入，否则导航被去重、守卫不触发
    await router.push('/')
    await router.push('/admin')
    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query.redirect).toBe('/admin')
  })
})
