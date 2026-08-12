<script setup lang="ts">
/**
 * 批次管理页 — 入库收货生成的批次（批次号 = 入库单号-明细id）
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Box, Warning, Download, Goods } from '@element-plus/icons-vue'
import { getBatches, type BatchRow } from '@/api'
import SummaryCards, { GRADIENTS } from '@/components/SummaryCards.vue'

// ============ 多维度汇总（Mock） ============
const summaryCards = [
  { label: '活跃批次数', value: 486, unit: '个', icon: Box, gradient: GRADIENTS.cyan },
  { label: '临期批次', value: 18, unit: '个', icon: Warning, gradient: GRADIENTS.red },
  { label: '本月入库批次', value: 92, unit: '个', icon: Download, gradient: GRADIENTS.indigo },
  { label: '批次总数量', value: 24580, unit: '件', icon: Goods, gradient: GRADIENTS.blue },
]

const batches = ref<BatchRow[]>([])
const keyword = ref('')
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const loadBatches = async () => {
  loading.value = true
  try {
    const res = await getBatches({ keyword: keyword.value || undefined, page: page.value, pageSize: pageSize.value })
    batches.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载批次失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const onSearch = () => {
  page.value = 1
  loadBatches()
}

const formatTime = (t: string | null) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(loadBatches)
</script>

<template>
  <div>
    <!-- 多维度汇总 KPI（Mock） -->
    <SummaryCards :cards="summaryCards" />

    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-input v-model="keyword" placeholder="批次号 / 商品名称 / SKU" style="width: 300px" clearable
        @clear="onSearch" @keyup.enter="onSearch" />
      <el-button type="primary" @click="onSearch">查询</el-button>
    </div>

    <el-table :data="batches" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="batchNo" label="批次号" width="200" />
      <el-table-column prop="productName" label="商品名称" min-width="140" />
      <el-table-column prop="sku" label="SKU" width="120" />
      <el-table-column label="入库上架日期" width="180">
        <template #default="{ row }">{{ formatTime(row.inboundDate) }}</template>
      </el-table-column>
      <el-table-column label="生产日期" width="180">
        <template #default="{ row }">{{ formatTime(row.manufactureDate) }}</template>
      </el-table-column>
      <el-table-column label="有效期至" width="180">
        <template #default="{ row }">{{ formatTime(row.expiryDate) }}</template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadBatches()"
      />
    </div>
  </div>
</template>
