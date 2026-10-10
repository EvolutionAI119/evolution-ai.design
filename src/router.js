import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/designer', name: 'Designer', component: () => import('./views/Designer.vue') },
  { path: '/copilot', name: 'DesignCopilot', component: () => import('./views/DesignCopilot.vue') },
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
  // 联系方式（替代封存中的账户模块）
  { path: '/contact', name: 'Contact',
    component: () => import('./views/Contact.vue') },
  // 账户体系（封存中）：登录/账户页不再注册路由，源码保留于 views/ 备查
  // 管理后台：游客模式期间由后端 guest 账户（superadmin）直接放行
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

// 全局守卫（封存期）：账号模块已移除，游客身份由前端预置 + 后端 GUEST_MODE 统一放行。
// 保留空守卫作为事件钩子的占位，以便后续复启登录体系时恢复检查逻辑。
router.beforeEach(async () => {
  return true
})

export default router
