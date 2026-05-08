import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/products',
    },
    {
      path: '/products',
      name: 'Products',
      component: () => import('@/views/ProductsView.vue'),
    },
    {
      path: '/inventory',
      name: 'Inventory',
      component: () => import('@/views/InventoryView.vue'),
    },
    {
      path: '/inbound',
      name: 'Inbound',
      component: () => import('@/views/InboundView.vue'),
    },
  ],
})

export default router
