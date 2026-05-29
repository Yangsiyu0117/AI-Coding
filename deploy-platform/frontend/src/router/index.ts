import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/services',
      name: 'ServiceList',
      component: () => import('../views/ServiceList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/packages',
      name: 'PackageList',
      component: () => import('../views/PackageList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/upgrade/new',
      name: 'UpgradeNew',
      component: () => import('../views/UpgradeNew.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/upgrade/:id',
      name: 'UpgradeDetail',
      component: () => import('../views/UpgradeDetail.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/upgrades',
      name: 'UpgradeHistory',
      component: () => import('../views/UpgradeHistory.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/patrol',
      name: 'Patrol',
      component: () => import('../views/Patrol.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/audit',
      name: 'AuditLog',
      component: () => import('../views/AuditLog.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/Settings.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
