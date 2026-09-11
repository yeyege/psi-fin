<script setup lang="ts">
/**
 * 销售订单页 — 草稿 → 确认 → 发货（自动生成应收）→ 完成 / 作废
 * 业财一体收入侧闭环的入口
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  getSalesOrders, createSalesOrder, confirmSalesOrder, shipSalesOrder,
  completeSalesOrder, cancelSalesOrder, getCustomers, getProducts,
  type SalesOrder, type SalesOrderItemPayload,
} from '@/api'

const STATUS_LABEL: Record<string, string> = {
  DRAFT: '草稿', CONFIRMED: '已确认', SHIPPED: '已发货', COMPLETED: '已完成', CANCELLED: '已作废',
}
const STATUS_TYPE: Record<string, string> = {
  DRAFT: 'info', CONFIRMED: 'warning', SHIPPED: 'primary', COMPLETED: 'success', CANCELLED: 'danger',
}

const orders = ref<SalesOrder[]>([])
const loading = ref(false)
const status = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const customers = ref<Array<{ id: number; name: string }>>([])
const products = ref<Array<{ id: number; name: string; sku: string }>>([])

const load = async () => {
  loading.value = true
  try {
    const res = await getSalesOrders({
      status: status.value || undefined,
      keyword: keyword.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    orders.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const loadOptions = async () => {
  try {
    const [c, p] = await Promise.all([
      getCustomers({ page: 1, pageSize: 100 }),
      getProducts({ page: 1, pageSize: 100 }),
    ])
    customers.value = c.data.list.map((x) => ({ id: x.id, name: x.name }))
    products.value = p.data.list.map((x) => ({ id: x.id, name: x.name, sku: x.sku }))
  } catch {
    // 选项加载失败不阻塞主流程
  }
}

// ============ 新建订单 ============
const dialogVisible = ref(false)
const submitting = ref(false)
const form = ref<{
  customerId: number | null
  creditDays: number
  remark: string
  items: Array<{ productId: number | null; quantity: number; unitPrice: number }>
}>({ customerId: null, creditDays: 0, remark: '', items: [{ productId: null, quantity: 1, unitPrice: 0 }] })

const formTotal = computed(() =>
  form.value.items.reduce((sum, i) => sum + (Number(i.quantity) || 0) * (Number(i.unitPrice) || 0), 0),
)

const handleAdd = () => {
  form.value = { customerId: null, creditDays: 0, remark: '', items: [{ productId: null, quantity: 1, unitPrice: 0 }] }
  dialogVisible.value = true
}
const addItem = () => form.value.items.push({ productId: null, quantity: 1, unitPrice: 0 })
const removeItem = (idx: number) => {
  if (form.value.items.length <= 1) return ElMessage.warning('至少保留一条明细')
  form.value.items.splice(idx, 1)
}

const handleSubmit = async () => {
  if (!form.value.customerId) return ElMessage.warning('请选择客户')
  const items: SalesOrderItemPayload[] = form.value.items
    .filter((i) => i.productId)
    .map((i) => ({ productId: i.productId as number, quantity: Number(i.quantity), unitPrice: Number(i.unitPrice) }))
  if (!items.length) return ElMessage.warning('请至少选择一条商品明细')
  submitting.value = true
  try {
    await createSalesOrder({
      customerId: form.value.customerId,
      creditDays: Number(form.value.creditDays) || 0,
      items,
      remark: form.value.remark || undefined,
    })
    ElMessage.success('订单已创建（草稿）')
    dialogVisible.value = false
    page.value = 1
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

// ============ 状态流转 ============
const doAction = async (row: SalesOrder, action: 'confirm' | 'ship' | 'complete' | 'cancel') => {
  const tips: Record<string, string> = {
    confirm: '确认该订单？确认后明细将不可修改。',
    ship: '确认发货？发货后将自动生成应收（到期日 = 发货日 + 账期）。',
    complete: '标记该订单为已完成？',
    cancel: '作废该订单？仅草稿/已确认可作废。',
  }
  try {
    await ElMessageBox.confirm(tips[action], '操作确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    if (action === 'confirm') await confirmSalesOrder(row.id)
    else if (action === 'ship') await shipSalesOrder(row.id)
    else if (action === 'complete') await completeSalesOrder(row.id)
    else await cancelSalesOrder(row.id)
    ElMessage.success('操作成功')
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const onPageChange = (p: number) => { page.value = p; load() }

onMounted(() => { load(); loadOptions() })
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <el-select v-model="status" placeholder="全部状态" clearable style="width: 150px"
        @change="page = 1; load()">
        <el-option v-for="(label, key) in STATUS_LABEL" :key="key" :label="label" :value="key" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索订单号/客户..." style="width: 240px" clearable
        @keyup.enter="page = 1; load()" @clear="page = 1; load()" />
      <el-button type="primary" @click="page = 1; load()">搜索</el-button>
      <el-button type="success" :icon="Plus" @click="handleAdd">新建订单</el-button>
    </div>

    <el-table :data="orders" v-loading="loading" border stripe>
      <el-table-column prop="orderNo" label="订单号" width="170" />
      <el-table-column prop="customerName" label="客户" min-width="160" />
      <el-table-column label="账期" width="90">
        <template #default="{ row }">{{ row.creditDays }} 天</template>
      </el-table-column>
      <el-table-column label="订单金额" width="130" align="right">
        <template #default="{ row }">¥{{ row.totalAmount.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_TYPE[row.status] || 'info'">{{ STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发货时间" width="170">
        <template #default="{ row }">{{ row.shippedAt ? row.shippedAt.replace('T', ' ').slice(0, 19) : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'DRAFT'" size="small" type="warning" @click="doAction(row, 'confirm')">确认</el-button>
          <el-button v-if="row.status === 'CONFIRMED'" size="small" type="primary" @click="doAction(row, 'ship')">发货</el-button>
          <el-button v-if="row.status === 'SHIPPED'" size="small" type="success" @click="doAction(row, 'complete')">完成</el-button>
          <el-button v-if="['DRAFT', 'CONFIRMED'].includes(row.status)" size="small" type="danger" @click="doAction(row, 'cancel')">作废</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next, jumper" @current-change="onPageChange" />
    </div>

    <el-dialog v-model="dialogVisible" title="新建销售订单" width="760px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="客户">
          <el-select v-model="form.customerId" placeholder="选择客户" filterable style="width: 100%">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="账期(天)">
          <el-input-number v-model="form.creditDays" :min="0" :max="365" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px">发货后按此计算应收到期日</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" maxlength="200" />
        </el-form-item>
        <el-form-item label="商品明细">
          <div style="width: 100%">
            <el-table :data="form.items" size="small" border>
              <el-table-column label="商品" min-width="200">
                <template #default="{ row }">
                  <el-select v-model="row.productId" placeholder="选择商品" filterable>
                    <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="数量" width="130">
                <template #default="{ row }">
                  <el-input-number v-model="row.quantity" :min="1" :max="999999" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="单价" width="150">
                <template #default="{ row }">
                  <el-input-number v-model="row.unitPrice" :min="0" :precision="2" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="金额" width="120" align="right">
                <template #default="{ row }">¥{{ ((row.quantity || 0) * (row.unitPrice || 0)).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="" width="70">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" :icon="Delete" circle @click="removeItem($index)" />
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" :icon="Plus" style="margin-top: 8px" @click="addItem">添加明细</el-button>
          </div>
        </el-form-item>
        <el-form-item label="订单金额">
          <span style="font-size: 18px; font-weight: 600; color: #f56c6c">¥{{ formTotal.toFixed(2) }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">创建订单</el-button>
      </template>
    </el-dialog>
  </div>
</template>
