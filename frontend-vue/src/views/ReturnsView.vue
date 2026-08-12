<script setup lang="ts">
/**
 * 退货管理页 — 状态机：PENDING(待收货) → RECEIVED(已收货登记) → DONE(处理完成)
 * 支持 FBA退货 / 买家退件 / 服务商退件；
 * 收货时 RESELL/RELABEL 明细转正品累加库存，SCRAP 报废只登记。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createReturnOrder, receiveReturnOrder, finishReturnOrder, getReturnOrders,
  getProducts, getLocations, getCustomers,
  type ReturnOrder, type ReturnItemRequest, type Product, type Location, type Customer,
} from '@/api'

const orders = ref<ReturnOrder[]>([])
const statusFilter = ref('')
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  customerId: 0,
  source: 'FBA',
  remark: '',
  items: [] as Array<ReturnItemRequest & { key: number }>,
})
let itemKey = 0

const products = ref<Product[]>([])
const locations = ref<Location[]>([])
const customers = ref<Customer[]>([])

const STATUS_MAP: Record<string, { label: string; type: 'info' | 'warning' | 'success' }> = {
  PENDING: { label: '待收货', type: 'info' },
  RECEIVED: { label: '已收货', type: 'warning' },
  DONE: { label: '已完成', type: 'success' },
}

const SOURCE_LABEL: Record<string, string> = {
  FBA: 'FBA退货',
  SELLER: '买家退件',
  CARRIER: '服务商退件',
}

const DISPOSITION_LABEL: Record<string, { label: string; type: 'success' | 'warning' | 'danger' }> = {
  RESELL: { label: '转正品', type: 'success' },
  RELABEL: { label: '换标', type: 'warning' },
  SCRAP: { label: '报废', type: 'danger' },
}

const loadOrders = async () => {
  loading.value = true
  try {
    const res = await getReturnOrders({ status: statusFilter.value || undefined, page: page.value, pageSize: pageSize.value })
    orders.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载退货单失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const addItem = () => {
  form.items.push({ key: ++itemKey, productId: 0, quantity: 1, locationCode: '', disposition: 'RESELL' })
}

const removeItem = (key: number) => {
  form.items = form.items.filter((i) => i.key !== key)
}

const openCreate = () => {
  form.customerId = 0
  form.source = 'FBA'
  form.remark = ''
  form.items = []
  addItem()
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (!form.customerId) return ElMessage.warning('请选择客户')
  if (form.items.some((i) => !i.productId || !i.locationCode || i.quantity <= 0)) {
    return ElMessage.warning('请完整填写商品、库位与数量')
  }
  submitting.value = true
  try {
    const payload = {
      customerId: form.customerId,
      source: form.source,
      remark: form.remark || undefined,
      items: form.items.map(({ productId, quantity, locationCode, disposition }) => ({ productId, quantity, locationCode, disposition })),
    }
    const res = await createReturnOrder(payload)
    ElMessage.success(`退货单 ${res.data.orderNo} 创建成功`)
    dialogVisible.value = false
    page.value = 1
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

const receive = async (row: ReturnOrder) => {
  try {
    const res = await receiveReturnOrder(row.id)
    ElMessage.success(`收货完成：${res.data.orderNo}，转正品库存已生效`)
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '收货失败')
  }
}

const finish = async (row: ReturnOrder) => {
  try {
    await finishReturnOrder(row.id)
    ElMessage.success(`退货单 ${row.orderNo} 处理完成`)
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(async () => {
  const [pRes, lRes, cRes] = await Promise.all([
    getProducts({ page: 1, pageSize: 100 }),
    getLocations({}),
    getCustomers({ page: 1, pageSize: 100 }),
  ])
  products.value = pRes.data.list
  locations.value = lRes.data
  customers.value = cRes.data.list
  await loadOrders()
})
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 160px" @change="page = 1; loadOrders()">
        <el-option label="待收货" value="PENDING" />
        <el-option label="已收货" value="RECEIVED" />
        <el-option label="已完成" value="DONE" />
      </el-select>
      <el-button type="success" @click="openCreate">新建退货单</el-button>
      <el-button type="primary" @click="loadOrders">刷新</el-button>
    </div>

    <el-table :data="orders" v-loading="loading" border stripe>
      <el-table-column prop="orderNo" label="退货单号" width="190" />
      <el-table-column prop="customerName" label="客户" min-width="150" />
      <el-table-column label="来源" width="110">
        <template #default="{ row }">{{ SOURCE_LABEL[row.source] || row.source }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_MAP[row.status]?.type || 'info'">{{ STATUS_MAP[row.status]?.label || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="明细" min-width="260">
        <template #default="{ row }">
          <el-tag v-for="(it, i) in row.items" :key="i" size="small"
            :type="DISPOSITION_LABEL[it.disposition]?.type || 'info'" style="margin: 2px">
            {{ it.productName }} ×{{ it.quantity }} @ {{ it.locationCode }} ({{ DISPOSITION_LABEL[it.disposition]?.label || it.disposition }})
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'PENDING'" size="small" type="primary" @click="receive(row)">收货</el-button>
          <el-button v-if="row.status === 'RECEIVED'" size="small" type="success" @click="finish(row)">完成</el-button>
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

    <!-- 新建退货单 -->
    <el-dialog v-model="dialogVisible" title="新建退货单" width="720px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="客户">
          <el-select v-model="form.customerId" placeholder="选择客户" filterable style="width: 260px">
            <el-option v-for="c in customers" :key="c.id" :label="`${c.name} (${c.code})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="退货来源">
          <el-radio-group v-model="form.source">
            <el-radio-button value="FBA">FBA退货</el-radio-button>
            <el-radio-button value="SELLER">买家退件</el-radio-button>
            <el-radio-button value="CARRIER">服务商退件</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="明细">
          <div style="width: 100%">
            <div v-for="(item, idx) in form.items" :key="item.key" style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap">
              <el-select v-model="item.productId" placeholder="商品" filterable style="width: 170px">
                <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
              </el-select>
              <el-input-number v-model="item.quantity" :min="1" style="width: 110px" />
              <el-select v-model="item.locationCode" placeholder="目标库位" style="width: 130px">
                <el-option v-for="l in locations" :key="l.code" :label="l.code" :value="l.code" />
              </el-select>
              <el-select v-model="item.disposition" style="width: 110px">
                <el-option label="转正品" value="RESELL" />
                <el-option label="换标" value="RELABEL" />
                <el-option label="报废" value="SCRAP" />
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
