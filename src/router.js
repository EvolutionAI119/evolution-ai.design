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
  // 账户体系
  {
    path: '/login', name: 'Login',
    component: () => import('./views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/account', name: 'Account',
    component: () => import('./views/Account.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局守卫：未登录访问受保护页面 → 跳转登录并携带回跳地址
router.beforeEach((to) => {
  const token = localStorage.getItem('evoai_token')
  if (!to.meta.public && !token) {
    return { name: 'Login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  // 已登录用户访问登录页 → 直接回首页
  if (to.name === 'Login' && token) {
    return { path: '/' }
  }
  return true
})

export default router
