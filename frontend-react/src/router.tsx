import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from './App'
import ProductsPage from './pages/ProductsPage'
import InventoryPage from './pages/InventoryPage'
import InboundPage from './pages/InboundPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/products" replace /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'inventory', element: <InventoryPage /> },
      { path: 'inbound', element: <InboundPage /> },
    ],
  },
])

export default router
