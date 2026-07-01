import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('../views/Projects.vue')
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: () => import('../views/ProjectDetail.vue')
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('../views/Models.vue')
  },
  {
    path: '/designer',
    name: 'Designer',
    component: () => import('../views/Designer.vue')
  },
  {
    path: '/export',
    name: 'Export',
    component: () => import('../views/Export.vue')
  },
  {
    path: '/variants',
    name: 'Variants',
    component: () => import('../views/Variants.vue')
  },
  {
    path: '/workflow',
    name: 'Workflow',
    component: () => import('../views/Workflow.vue')
  },
  {
    path: '/quality',
    name: 'Quality',
    component: () => import('../views/Quality.vue')
  },
  {
    path: '/parameters',
    name: 'Parameters',
    component: () => import('../views/Parameters.vue')
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('../views/Reports.vue')
  },
  {
    path: '/handover',
    name: 'Handover',
    component: () => import('../views/Handover.vue')
  },
  {
    path: '/modify',
    name: 'Modify',
    component: () => import('../views/Modify.vue')
  },
  {
    path: '/demo',
    name: 'Demo',
    component: () => import('../views/Demo.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router