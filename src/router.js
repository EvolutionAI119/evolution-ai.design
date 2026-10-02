import { createRouter, createWebHashHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './stores/auth'
import i18n from './i18n'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/designer', name: 'Designer', component: () => import('./views/Designer.vue') },
  { path: '/projects', name: 'Projects', component: () => import('./views/Projects.vue') },
  { path: '/projects/:id', name: 'ProjectDetail', component: () => import('./views/ProjectDetail.vue') },
  { path: '/deep-learning', name: 'DeepLearning', component: () => import('./views/DeepLearning.vue') },
  { path: '/quality', name: 'Quality', component: () => import('./views/Quality.vue') },
  { path: '/deliver', name: 'Deliver', component: () => import('./views/Deliver.vue') },
  { path: '/demo', name: 'Demo', component: () => import('./views/Demo.vue') },
  { path: '/help', name: 'Help', component: () => import('./views/Help.vue') },
  // 社区（公开页：帖子 / 回复 / 点赞 / 引用线索提交）
  { path: '/community', name: 'Community',
    component: () => import('./views/Community.vue') },
  // 账户体系
  {
    path: '/login', name: 'Login',
    component: () => import('./views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/account', name: 'Account',
    component: () => import('./views/Account.vue'),
    // 账户页管理个人 Token：仅测试/商业用户与管理员需要登录
    meta: { requiresAuth: true }
  },
  // 管理后台：仅管理员（admin / superadmin）可进入
  {
    path: '/admin', name: 'Admin',
    component: () => import('./views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局守卫：平台默认免登录游客可浏览全部页面；
// 仅当路由显式声明 meta.requiresAuth 时才要求登录（如账户设置/管理后台），
// meta.requiresAdmin 时额外校验管理员角色（防止越权访问）。
router.beforeEach(async (to) => {
  // 登录态仅存内存（会话级），从 store 读取；不再读取 localStorage
  const auth = useAuthStore()
  const token = auth.token
  if (to.meta.requiresAuth && !token) {
    return {
      name: 'Login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }
  if (to.meta.requiresAdmin) {
    // 页面刷新后 user 可能尚未加载：先拉取当前用户再判定角色
    if (token && !auth.user) {
      try {
        await auth.fetchMe()
      } catch {
        return { name: 'Login', query: { redirect: to.fullPath } }
      }
    }
    if (!auth.isAdmin) {
      ElMessage.warning(i18n.global.t('common.adminOnly'))
      return { name: 'Dashboard' }
    }
  }
  return true
})

export default router
