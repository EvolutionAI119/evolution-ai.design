import { createRouter, createWebHashHistory } from 'vue-router'

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
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局守卫：平台默认免登录游客可浏览全部页面；
// 仅当路由显式声明 meta.requiresAuth 时才要求登录（如账户设置）。
router.beforeEach((to) => {
  const token = localStorage.getItem('evoai_token')
  if (to.meta.requiresAuth && !token) {
    return {
      name: 'Login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }
  return true
})

export default router
