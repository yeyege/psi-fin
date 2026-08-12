<script setup lang="ts">
/**
 * 出库管理页 — 状态机：PENDING(待拣货) → PICKED(已拣货锁定) → REVIEWED(已复核) → SHIPPED(已发货扣减)
 * 拣货时原子锁定防超卖；复核验货后发货扣减锁定库存。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createOutboundOrder, pickOutboundOrder, reviewOutboundOrder, shipOutboundOrder, getOutboundOrders,
  getProducts, getLocations,
  type OutboundOrder, type OutboundItemRequest, type Product, type Location,
} from '@/api'

const orders = ref<OutboundOrder[]>([])
const statusFilter = ref('')
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  customerName: '',
  remark: '',
  items: [] as Array<OutboundItemRequest & { key: number }>,
})
let itemKey = 0

const products = ref<Product[]>([])
const locations = ref<Location[]>([])

const STATUS_MAP: Record<string, { label: string; type: 'info' | 'warning' | 'success' }> = {
  PENDING: { label: '待拣货', type: 'info' },
  PICKED: { label: '已拣货', type: 'warning' },
  REVIEWED: { label: '已复核', type: 'warning' },
  SHIPPED: { label: '已发货', type: 'success' },
}

const loadOrders = async () => {
  loading.value = true
  try {
    const res = await getOutboundOrders({ status: statusFilter.value || undefined, page: page.value, pageSize: pageSize.value })
    orders.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载出库单失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const addItem = () => {
  form.items.push({ key: ++itemKey, productId: 0, quantity: 1, locationCode: '' })
}

const removeItem = (key: number) => {
  form.items = form.items.filter((i) => i.key !== key)
}

const openCreate = () => {
  form.customerName = ''
  form.remark = ''
  form.items = []
  addItem()
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (!form.customerName.trim()) return ElMessage.warning('请填写客户')
  if (form.items.some((i) => !i.productId || !i.locationCode || i.quantity <= 0)) {
    return ElMessage.warning('请完整填写商品、库位与数量')
  }
  submitting.value = true
  try {
    const payload = {
      customerName: form.customerName,
      remark: form.remark || undefined,
      items: form.items.map(({ productId, quantity, locationCode }) => ({ productId, quantity, locationCode })),
    }
    const res = await createOutboundOrder(payload)
    ElMessage.success(`出库单 ${res.data.orderNo} 创建成功`)
    dialogVisible.value = false
    page.value = 1
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

const pick = async (row: OutboundOrder) => {
  try {
    const res = await pickOutboundOrder(row.id)
    ElMessage.success(`拣货完成：${res.data.orderNo}，库存已锁定`)
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '拣货失败')
  }
}

const review = async (row: OutboundOrder) => {
  try {
    const res = await reviewOutboundOrder(row.id)
    ElMessage.success(`复核完成：${res.data.orderNo}，可发货`)
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '复核失败')
  }
}

const ship = async (row: OutboundOrder) => {
  try {
    const res = await shipOutboundOrder(row.id)
    ElMessage.success(`发货完成：${res.data.orderNo}，库存已扣减`)
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发货失败')
  }
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(async () => {
  const [pRes, lRes] = await Promise.all([
    getProducts({ page: 1, pageSize: 100 }),
    getLocations({}),
  ])
  products.value = pRes.data.list
  locations.value = lRes.data
  await loadOrders()
})
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 160px" @change="page = 1; loadOrders()">
        <el-option label="待拣货" value="PENDING" />
        <el-option label="已拣货" value="PICKED" />
        <el-option label="已复核" value="REVIEWED" />
        <el-option label="已发货" value="SHIPPED" />
      </el-select>
      <el-button type="success" @click="openCreate">新建出库单</el-button>
      <el-button type="primary" @click="loadOrders">刷新</el-button>
    </div>

    <el-table :data="orders" v-loading="loading" border stripe>
      <el-table-column prop="orderNo" label="出库单号" width="190" />
      <el-table-column prop="customerName" label="客户" min-width="120" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="STATUS_MAP[row.status]?.type || 'info'">{{ STATUS_MAP[row.status]?.label || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="明细" min-width="240">
        <template #default="{ row }">
          <el-tag v-for="(it, i) in row.items" :key="i" size="small" style="margin: 2px">
            {{ it.productName }} ×{{ it.quantity }} @ {{ it.locationCode }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'PENDING'" size="small" type="primary" @click="pick(row)">拣货</el-button>
          <el-button v-if="row.status === 'PICKED'" size="small" type="warning" @click="review(row)">复核</el-button>
          <el-button v-if="row.status === 'REVIEWED'" size="small" type="success" @click="ship(row)">发货</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadOrders()"
      />
    </div>

    <!-- 新建出库单 -->
    <el-dialog v-model="dialogVisible" title="新建出库单" width="680px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="客户">
          <el-input v-model="form.customerName" placeholder="如 某某电商有限公司" />
        </el-form-item>
        <el-form-item label="明细">
          <div style="width: 100%">
            <div v-for="(item, idx) in form.items" :key="item.key" style="display: flex; gap: 8px; margin-bottom: 8px">
              <el-select v-model="item.productId" placeholder="商品" filterable style="width: 180px">
                <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
              </el-select>
              <el-input-number v-model="item.quantity" :min="1" style="width: 120px" />
              <el-select v-model="item.locationCode" placeholder="出库库位" style="width: 160px">
                <el-option v-for="l in locations" :key="l.code" :label="l.code" :value="l.code" />
              </el-select>
              <el-button type="danger" :icon="'Delete'" circle @click="removeItem(item.key)" />
              <el-button v-if="idx === form.items.length - 1" type="primary" link @click="addItem">+ 添加一行</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
