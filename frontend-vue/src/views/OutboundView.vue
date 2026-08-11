<script setup lang="ts">
/**
 * 出库管理页 — 选做 A
 *
 * 功能：客户名称 + 多行出库明细，提交后库存原子扣减。
 * 库存不足时后端返回 409，前端展示具体错误信息，单据不会被创建。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  getProducts,
  getWarehouses,
  getLocations,
  createOutboundOrder,
  type Product,
  type Warehouse,
  type Location,
} from '@/api'

interface OutboundRow {
  productId: number | undefined
  warehouseId: number | undefined
  locationCode: string
  quantity: number
  locations: Location[]
}

const formRef = ref<FormInstance>()
const form = reactive({ customerName: '' })
const products = ref<Product[]>([])
const warehouses = ref<Warehouse[]>([])
const items = ref<OutboundRow[]>([])
const submitting = ref(false)
const lastOrderNo = ref('')

const rules: FormRules = {
  customerName: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const [pRes, wRes] = await Promise.all([getProducts(), getWarehouses()])
    products.value = pRes.data
    warehouses.value = wRes.data
  } catch (e: any) {
    ElMessage.error('基础数据加载失败')
  }
})

const addItem = () => {
  items.value.push({
    productId: undefined,
    warehouseId: undefined,
    locationCode: '',
    quantity: 1,
    locations: [],
  })
}

const removeItem = (index: number) => {
  items.value.splice(index, 1)
}

const onWarehouseChange = async (row: OutboundRow) => {
  row.locationCode = ''
  row.locations = []
  if (!row.warehouseId) return
  try {
    const res = await getLocations(row.warehouseId)
    row.locations = res.data
  } catch (e: any) {
    ElMessage.error('库位加载失败')
  }
}

const validateItems = (): string | null => {
  if (items.value.length === 0) return '请至少添加一条出库明细'
  for (let i = 0; i < items.value.length; i++) {
    const row = items.value[i]
    if (!row.productId) return `第 ${i + 1} 行：请选择商品`
    if (!row.warehouseId) return `第 ${i + 1} 行：请选择仓库`
    if (!row.locationCode) return `第 ${i + 1} 行：请选择库位`
    if (!row.quantity || row.quantity <= 0) return `第 ${i + 1} 行：数量必须大于 0`
  }
  return null
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const err = validateItems()
  if (err) {
    ElMessage.warning(err)
    return
  }

  submitting.value = true
  try {
    const payload = {
      customerName: form.customerName,
      items: items.value.map((r) => ({
        productId: r.productId!,
        quantity: r.quantity,
        locationCode: r.locationCode,
      })),
    }
    const res = await createOutboundOrder(payload)
    lastOrderNo.value = res.data.orderNo
    ElMessage.success(`出库单创建成功：${res.data.orderNo}`)
    form.customerName = ''
    items.value = []
  } catch (e: any) {
    // 库存不足时后端返回 409 + detail，展示给用户
    const detail = e.response?.data?.detail || e.response?.data?.message || '出库失败'
    ElMessage.error('出库失败: ' + detail)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <h3>出库管理</h3>

    <el-alert
      v-if="lastOrderNo"
      :title="`最近一次出库单：${lastOrderNo}`"
      type="success"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      style="max-width: 1100px"
    >
      <el-form-item label="客户名称" prop="customerName">
        <el-input v-model="form.customerName" placeholder="请输入客户名称" maxlength="200" />
      </el-form-item>
    </el-form>

    <div style="margin-bottom: 12px">
      <el-button type="primary" @click="addItem">+ 添加明细</el-button>
      <span style="margin-left: 12px; color: #999; font-size: 13px">
        共 {{ items.length }} 条明细
      </span>
    </div>

    <el-table :data="items" border style="width: 100%" empty-text="请点击「添加明细」">
      <el-table-column label="序号" type="index" width="60" align="center" />
      <el-table-column label="商品" min-width="220">
        <template #default="{ row }">
          <el-select v-model="row.productId" placeholder="搜索商品名称/SKU" filterable style="width: 100%">
            <el-option
              v-for="p in products"
              :key="p.id"
              :label="`${p.name}（${p.sku}）`"
              :value="p.id"
            />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="仓库" width="180">
        <template #default="{ row }">
          <el-select
            v-model="row.warehouseId"
            placeholder="选择仓库"
            style="width: 100%"
            @change="onWarehouseChange(row)"
          >
            <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="库位" width="180">
        <template #default="{ row }">
          <el-select
            v-model="row.locationCode"
            placeholder="先选仓库"
            :disabled="!row.warehouseId"
            style="width: 100%"
          >
            <el-option
              v-for="loc in row.locations"
              :key="loc.code"
              :label="loc.code"
              :value="loc.code"
            />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="140">
        <template #default="{ row }">
          <el-input-number v-model="row.quantity" :min="1" :max="999999" controls-position="right" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" align="center">
        <template #default="{ $index }">
          <el-button type="danger" size="small" @click="removeItem($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 20px">
      <el-button
        type="success"
        :loading="submitting"
        :disabled="items.length === 0"
        @click="handleSubmit"
      >
        提交出库单
      </el-button>
    </div>
  </div>
</template>
