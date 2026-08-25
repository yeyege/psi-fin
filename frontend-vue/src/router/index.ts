import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue') },
    { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/products', name: 'Products', component: () => import('@/views/ProductsView.vue') },
    { path: '/customers', name: 'Customers', component: () => import('@/views/CustomersView.vue') },
    { path: '/warehouses', name: 'Warehouses', component: () => import('@/views/WarehousesView.vue') },
    { path: '/inventory', name: 'Inventory', component: () => import('@/views/InventoryView.vue') },
    { path: '/flows', name: 'Flows', component: () => import('@/views/FlowsView.vue') },
    { path: '/batches', name: 'Batches', component: () => import('@/views/BatchesView.vue') },
    { path: '/inbound', name: 'Inbound', component: () => import('@/views/InboundView.vue') },
    { path: '/outbound', name: 'Outbound', component: () => import('@/views/OutboundView.vue') },
    { path: '/waves', name: 'Waves', component: () => import('@/views/WavesView.vue') },
    { path: '/returns', name: 'Returns', component: () => import('@/views/ReturnsView.vue') },
    { path: '/transfers', name: 'Transfers', component: () => import('@/views/TransfersView.vue') },
    { path: '/adjustments', name: 'Adjustments', component: () => import('@/views/AdjustmentsView.vue') },
    { path: '/counts', name: 'Counts', component: () => import('@/views/CountsView.vue') },
    { path: '/users', name: 'Users', component: () => import('@/views/UsersView.vue'), meta: { admin: true } },
  ],
})

// 全局登录守卫：除 /login 外一律要求登录；/users 仅管理员
router.beforeEach((to) => {
  const token = localStorage.getItem('wms_token')
  const user = JSON.parse(localStorage.getItem('wms_user') || 'null')
  if (to.path === '/login') {
    return token ? '/dashboard' : true
  }
  if (!token) {
    return '/login'
  }
  if (to.meta.admin && user?.role !== 'admin') {
    return '/dashboard'
  }
  return true
})

export default router
