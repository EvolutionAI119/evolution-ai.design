// 路由守卫测试（账号封存期）：账户路由已移除、游客态默认放行全部页面
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 视图组件用桩替代（render 函数，避免依赖运行时模板编译器与重型依赖）
vi.mock('../views/Dashboard.vue', () => ({ default: { name: 'Dashboard', render: () => null } }))
vi.mock('../views/Contact.vue', () => ({ default: { name: 'Contact', render: () => null } }))
// 网络层不真正执行
vi.mock('../api', () => ({
  authAPI: { login: vi.fn(), register: vi.fn(), me: vi.fn() },
  setApiToken: vi.fn()
}))

import router from '../router'
import { useAuthStore } from '../stores/auth'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('模块封存：路由注册', () => {
  it('登录页与账户页路由已移除（源码保留于 views/ 备查）', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).not.toContain('Login')
    expect(names).not.toContain('Account')
  })

  it('Admin 已移出前端（后端 /admin 独立提供），SPA 不再注册该路由', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).not.toContain('Admin')
  })

  it('Contact 路由已注册（替代 Account 位置）', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).toContain('Contact')
  })
})

describe('路由守卫：游客态（封存期默认身份）', () => {
  it('可自由访问首页 Dashboard 与联系页 Contact', async () => {
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('Dashboard')
    await router.push('/contact')
    expect(router.currentRoute.value.name).toBe('Contact')
  })

  it('守卫无任何重定向（登录体系封存，全站游客可达）', async () => {
    for (const path of ['/', '/designer', '/projects', '/quality',
                        '/deliver', '/demo', '/community', '/help',
                        '/contact']) {
      const r = await router.push(path)
      // vue-router：返回 falsy 表示未被守卫重定向/中止
      expect(r).toBeFalsy()
    }
  })
})
