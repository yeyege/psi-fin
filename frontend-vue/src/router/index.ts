import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/inventory' },
    { path: '/products', name: 'Products', component: () => import('@/views/ProductsView.vue') },
    { path: '/warehouses', name: 'Warehouses', component: () => import('@/views/WarehousesView.vue') },
    { path: '/inventory', name: 'Inventory', component: () => import('@/views/InventoryView.vue') },
    { path: '/flows', name: 'Flows', component: () => import('@/views/FlowsView.vue') },
    { path: '/batches', name: 'Batches', component: () => import('@/views/BatchesView.vue') },
    { path: '/inbound', name: 'Inbound', component: () => import('@/views/InboundView.vue') },
    { path: '/outbound', name: 'Outbound', component: () => import('@/views/OutboundView.vue') },
    { path: '/transfers', name: 'Transfers', component: () => import('@/views/TransfersView.vue') },
    { path: '/adjustments', name: 'Adjustments', component: () => import('@/views/AdjustmentsView.vue') },
  ],
})

export default router
