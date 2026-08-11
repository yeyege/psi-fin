<script setup lang="ts">
/**
 * 库存查询页 — 任务2 实现
 *
 * 功能：
 * 1. 搜索栏：商品名称/SKU 模糊搜索（防抖 300ms）+ 仓库下拉筛选
 * 2. 表格：商品名称、SKU、库位编码、仓库、库存数量、更新时间
 * 3. 库存数量 < 10 的行整行高亮为红色
 * 4. 后端分页（避免大数据量一次性加载，对应选做 C）
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { getInventory, getWarehouses, type InventoryItem, type Warehouse } from '@/api'
import { LOW_STOCK_THRESHOLD, lowStockRowClass } from '@/utils/inventory'

const keyword = ref('')
const warehouseId = ref<number | undefined>()
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const inventoryList = ref<InventoryItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 防抖：关键词输入停止 300ms 后再查询，减少无效请求
let debounceTimer: ReturnType<typeof setTimeout> | null = null
const onKeywordInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    loadInventory()
  }, 300)
}

const loadInventory = async () => {
  loading.value = true
  try {
    const res = await getInventory({
      keyword: keyword.value || undefined,
      warehouseId: warehouseId.value,
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

// 仓库变更：重置到第 1 页再查询
const onWarehouseChange = () => {
  page.value = 1
  loadInventory()
}

// 分页变更
const onPageChange = (p: number) => {
  page.value = p
  loadInventory()
}

// 低库存行高亮 class 来自 @/utils/inventory（已抽离为纯函数，便于测试）

const formatTime = (t: string) => {
  if (!t) return '-'
  return t.replace('T', ' ').split('.')[0]
}

onMounted(async () => {
  try {
    const wRes = await getWarehouses()
    warehouses.value = wRes.data
  } catch (e: any) {
    ElMessage.error('仓库加载失败')
  }
  await loadInventory()
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div>
    <h3>库存查询</h3>

    <!-- 搜索栏 -->
    <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center">
      <el-input
        v-model="keyword"
        placeholder="搜索商品名称/SKU..."
        style="width: 300px"
        clearable
        @input="onKeywordInput"
        @clear="onKeywordInput"
        @keyup.enter="loadInventory"
      />
      <el-select
        v-model="warehouseId"
        placeholder="全部仓库"
        clearable
        style="width: 200px"
        @change="onWarehouseChange"
      >
        <el-option
          v-for="w in warehouses"
          :key="w.id"
          :label="w.name"
          :value="w.id"
        />
      </el-select>
      <el-button type="primary" @click="loadInventory">查询</el-button>
      <el-button @click="keyword = ''; warehouseId = undefined; onWarehouseChange()">重置</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      :data="inventoryList"
      v-loading="loading"
      border
      stripe
      :row-class-name="lowStockRowClass"
    >
      <el-table-column prop="productName" label="商品名称" min-width="160" />
      <el-table-column prop="sku" label="SKU" width="140" />
      <el-table-column prop="locationCode" label="库位编码" width="140" />
      <el-table-column prop="warehouseName" label="仓库" width="120" />
      <el-table-column prop="quantity" label="库存数量" width="110" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.quantity < LOW_STOCK_THRESHOLD ? '#f56c6c' : '', fontWeight: row.quantity < LOW_STOCK_THRESHOLD ? 700 : 400 }">
            {{ row.quantity }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="onPageChange"
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
