import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/designer', name: 'Designer', component: () => import('./views/Designer.vue') },
  { path: '/projects', name: 'Projects', component: () => import('./views/Projects.vue') },
  { path: '/deep-learning', name: 'DeepLearning', component: () => import('./views/DeepLearning.vue') },
  { path: '/quality', name: 'Quality', component: () => import('./views/Quality.vue') },
  { path: '/deliver', name: 'Deliver', component: () => import('./views/Deliver.vue') },
  { path: '/demo', name: 'Demo', component: () => import('./views/Demo.vue') }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
