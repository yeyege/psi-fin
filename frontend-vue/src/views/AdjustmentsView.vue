<script setup lang="ts">
/**
 * 库存调整页 — changeQty>0 盘盈 / <0 盘亏
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createAdjustment, getAdjustments,
  getProducts, getLocations,
  type AdjustmentOrder, type AdjustmentItemRequest, type Product, type Location,
} from '@/api'

const orders = ref<AdjustmentOrder[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  remark: '',
  items: [] as Array<AdjustmentItemRequest & { key: number }>,
})
let itemKey = 0

const products = ref<Product[]>([])
const locations = ref<Location[]>([])

const loadOrders = async () => {
  loading.value = true
  try {
    const res = await getAdjustments({ page: page.value, pageSize: pageSize.value })
    orders.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载调整单失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const addItem = () => {
  form.items.push({ key: ++itemKey, productId: 0, locationCode: '', changeQty: 0 })
}

const removeItem = (key: number) => {
  form.items = form.items.filter((i) => i.key !== key)
}

const openCreate = () => {
  form.remark = ''
  form.items = []
  addItem()
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (form.items.some((i) => !i.productId || !i.locationCode || i.changeQty === 0)) {
    return ElMessage.warning('请完整填写商品、库位，且调整数量不能为 0')
  }
  submitting.value = true
  try {
    const payload = {
      remark: form.remark || undefined,
      items: form.items.map(({ productId, locationCode, changeQty }) => ({ productId, locationCode, changeQty })),
    }
    const res = await createAdjustment(payload)
    ElMessage.success(`调整单 ${res.data.orderNo} 完成`)
    dialogVisible.value = false
    page.value = 1
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '调整失败')
  } finally {
    submitting.value = false
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
      <el-button type="success" @click="openCreate">新建调整单</el-button>
      <el-button type="primary" @click="loadOrders">刷新</el-button>
    </div>

    <el-table :data="orders" v-loading="loading" border stripe>
      <el-table-column prop="orderNo" label="调整单号" width="190" />
      <el-table-column label="明细" min-width="300">
        <template #default="{ row }">
          <el-tag v-for="(it, i) in row.items" :key="i" size="small" style="margin: 2px"
            :type="it.changeQty > 0 ? 'success' : 'danger'">
            {{ it.productName }} @ {{ it.locationCode }} {{ it.changeQty > 0 ? '+' : '' }}{{ it.changeQty }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
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

    <!-- 新建调整单 -->
    <el-dialog v-model="dialogVisible" title="新建库存调整单" width="680px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="明细">
          <div style="width: 100%">
            <div v-for="(item, idx) in form.items" :key="item.key" style="display: flex; gap: 8px; margin-bottom: 8px">
              <el-select v-model="item.productId" placeholder="商品" filterable style="width: 190px">
                <el-option v-for="p in products" :key="p.id" :label="`${p.name} (${p.sku})`" :value="p.id" />
              </el-select>
              <el-select v-model="item.locationCode" placeholder="库位" style="width: 150px">
                <el-option v-for="l in locations" :key="l.code" :label="l.code" :value="l.code" />
              </el-select>
              <el-input-number v-model="item.changeQty" :min="-99999" :max="99999" placeholder="正=盘盈 负=盘亏" style="width: 170px" />
              <el-button type="danger" :icon="'Delete'" circle @click="removeItem(item.key)" />
              <el-button v-if="idx === form.items.length - 1" type="primary" link @click="addItem">+ 添加一行</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" maxlength="200" placeholder="如 盘点差异" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
