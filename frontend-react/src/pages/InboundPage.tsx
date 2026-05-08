/**
 * ============================================
 *  入库管理页 — 候选人需要实现（任务1）
 * ============================================
 *
 * 需求：
 * 1. 表单：供应商名称 + 入库明细列表
 * 2. 明细行：商品下拉搜索 → 仓库 → 库位级联 → 数量
 * 3. 提交
 *
 * 建议使用 AI 协作，参考 ProductsPage.tsx 的实现风格
 */
import { useState } from 'react'
import { Form, Input, Button, Select, InputNumber, Space, message } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { createInboundOrder } from '@/api'

export default function InboundPage() {
  const [supplierName, setSupplierName] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [submitting, setSubmitting] = useState(false)

  // TODO: 候选人实现逻辑

  const addItem = () => {
    setItems([...items, { productId: undefined, quantity: 1, locationCode: '' }])
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    // TODO: 候选人实现
    message.info('请实现入库功能（任务1）')
  }

  return (
    <div>
      <h3> 入库管理</h3>

      <Form layout="vertical" style={{ maxWidth: 800 }}>
        <Form.Item label="供应商名称" required>
          <Input
            placeholder="请输入供应商名称"
            value={supplierName}
            onChange={(e) => setSupplierName(e.target.value)}
          />
        </Form.Item>

        <Form.Item label="入库明细">
          <Button type="primary" icon={<PlusOutlined />} onClick={addItem}>添加明细</Button>
        </Form.Item>
      </Form>

      {items.map((item, index) => (
        <div key={index} style={{ marginBottom: 12, display: 'flex', gap: 12, alignItems: 'center' }}>
          {/* TODO: 商品下拉选择 */}
          {/* TODO: 仓库 → 库位级联 */}
          {/* TODO: 数量输入 */}
          <Button danger icon={<DeleteOutlined />} onClick={() => removeItem(index)} />
        </div>
      ))}

      <Button
        type="primary"
        size="large"
        loading={submitting}
        onClick={handleSubmit}
        disabled={items.length === 0}
      >
        提交入库单
      </Button>

      {items.length === 0 && (
        <div style={{ marginTop: 24, color: '#999' }}>请点击"添加明细"按钮添加入库商品</div>
      )}
    </div>
  )
}
