<script setup lang="ts">
/**
 * 库存查询页（对标领星WMS：可用量 available + 锁定量 locked）
 *
 * - 视图切换：按商品(product)汇总 / 按库位(location)明细（含批次）
 * - 过滤：商品名称/SKU 模糊搜索 + 仓库下拉 + 批次号
 * - 低库存（总量 < 10）整行高亮
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Goods, Box, Warning, Lock } from '@element-plus/icons-vue'
import { getInventory, getWarehouses, type InventoryRow, type Warehouse } from '@/api'
import { LOW_STOCK_THRESHOLD, lowStockRowClass } from '@/utils/inventory'
import SummaryCards, { GRADIENTS } from '@/components/SummaryCards.vue'

// ============ 多维度汇总（Mock，全局口径，非分页数据） ============
const summaryCards = [
  { label: '总库存量', value: 58420, unit: '件', icon: Goods, gradient: GRADIENTS.cyan },
  { label: '在售 SKU 数', value: 326, unit: '个', icon: Box, gradient: GRADIENTS.purple },
  { label: '低库存商品', value: 12, unit: '个', icon: Warning, gradient: GRADIENTS.red },
  { label: '锁定占比', value: 6.8, unit: '%', icon: Lock, gradient: GRADIENTS.blue },
]
const formatNumber = (n: number) => n.toLocaleString('zh-CN')

const view = ref<'product' | 'location'>('product')
const keyword = ref('')
const warehouseId = ref<number>()
const batchNo = ref('')
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const inventoryList = ref<InventoryRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const loadInventory = async () => {
  loading.value = true
  try {
    const res = await getInventory({
      view: view.value,
      keyword: keyword.value || undefined,
      warehouseId: warehouseId.value,
      batchNo: batchNo.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    inventoryList.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载库存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const onViewChange = () => {
  page.value = 1
  loadInventory()
}

const onSearch = () => {
  page.value = 1
  loadInventory()
}

// 搜索防抖：关键词停止输入 300ms 后才发起查询，避免每次击键都请求后端
let searchTimer: number | undefined
const onKeywordInput = () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(onSearch, 300)
}

onBeforeUnmount(() => window.clearTimeout(searchTimer))

const onReset = () => {
  keyword.value = ''
  warehouseId.value = undefined
  batchNo.value = ''
  page.value = 1
  loadInventory()
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(async () => {
  try {
    const wRes = await getWarehouses()
    warehouses.value = wRes.data
  } catch {
    ElMessage.error('仓库加载失败')
  }
  await loadInventory()
})
</script>

<template>
  <div>
    <!-- 多维度汇总 KPI（Mock） -->
    <SummaryCards :cards="summaryCards" />

    <!-- 搜索栏 -->
    <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap">
      <el-radio-group v-model="view" @change="onViewChange">
        <el-radio-button value="product">按商品汇总</el-radio-button>
        <el-radio-button value="location">按库位明细</el-radio-button>
      </el-radio-group>
      <el-input v-model="keyword" placeholder="搜索商品名称/SKU..." style="width: 240px" clearable @input="onKeywordInput" @clear="onSearch" @keyup.enter="onSearch" />
      <el-select v-model="warehouseId" placeholder="全部仓库" clearable style="width: 180px" @change="onSearch">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-input v-if="view === 'location'" v-model="batchNo" placeholder="批次号" style="width: 180px" clearable
        @clear="onSearch" @keyup.enter="onSearch" />
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button @click="onReset">重置</el-button>
    </div>

    <el-table :data="inventoryList" v-loading="loading" border stripe :row-class-name="lowStockRowClass">
      <el-table-column prop="productName" label="商品名称" min-width="150" />
      <el-table-column prop="sku" label="SKU" width="130" />
      <el-table-column prop="warehouseName" label="仓库" width="120" />
      <el-table-column v-if="view === 'location'" prop="locationCode" label="库位编码" width="130" />
      <el-table-column v-if="view === 'location'" prop="batchNo" label="批次号" width="180" />
      <el-table-column label="可用量" width="100" align="right">
        <template #default="{ row }">{{ row.availableQty }}</template>
      </el-table-column>
      <el-table-column label="锁定量" width="100" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.lockedQty > 0 ? '#e6a23c' : '' }">{{ row.lockedQty }}</span>
        </template>
      </el-table-column>
      <el-table-column label="总库存" width="110" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.totalQty < LOW_STOCK_THRESHOLD ? '#f56c6c' : '', fontWeight: 700 }">
            {{ row.totalQty }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadInventory()"
      />
    </div>

    <el-empty v-if="!loading && inventoryList.length === 0" description="暂无库存数据" />
  </div>
</template>

<style scoped>
:deep(.low-stock-row) {
  background-color: #fef0f0 !important;
}
</style>
