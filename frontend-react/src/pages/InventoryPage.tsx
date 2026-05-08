/**
 * ============================================
 *  库存查询页 — 候选人需要实现（任务2）
 * ============================================
 *
 * 需求：
 * 1. 搜索栏：商品名称/SKU 模糊搜索 + 仓库下拉筛选
 * 2. 表格展示 + 库存 < 10 红色高亮
 * 3. 分页
 *
 * 建议使用 AI 协作，参考 ProductsPage.tsx 的实现风格
 */
import { useState } from 'react'
import { Table, Input, Select, Button, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getInventory, type InventoryItem, getWarehouses, type Warehouse } from '@/api'

export default function InventoryPage() {
  const [keyword, setKeyword] = useState('')
  const [warehouseId, setWarehouseId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<InventoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const pageSize = 20

  // TODO: 候选人实现 loadInventory
  const loadInventory = async () => { /* 调用 getInventory */ }

  // TODO: 候选人实现行样式
  const getRowClassName = (_: any, index: number) => ''

  const columns: ColumnsType<InventoryItem> = [
    { title: '商品名称', dataIndex: 'productName' },
    { title: 'SKU', dataIndex: 'sku', width: 150 },
    { title: '库位编码', dataIndex: 'locationCode', width: 150 },
    { title: '仓库', dataIndex: 'warehouseName', width: 120 },
    { title: '库存数量', dataIndex: 'quantity', width: 100 },
    { title: '更新时间', dataIndex: 'updatedAt', width: 180 },
  ]

  return (
    <div>
      <h3> 库存查询</h3>

      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索商品名称/SKU..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
        <Select
          placeholder="选择仓库"
          allowClear
          style={{ width: 200 }}
          value={warehouseId}
          onChange={setWarehouseId}
          options={warehouses.map((w) => ({ label: w.name, value: w.id }))}
        />
        <Button type="primary" onClick={loadInventory}>查询</Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="productId"
        loading={loading}
        rowClassName={getRowClassName}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p) => { setPage(p); loadInventory() },
          showTotal: (t) => `共 ${t} 条`,
        }}
        locale={{ emptyText: '暂无库存数据，请先完成入库操作' }}
      />
    </div>
  )
}
