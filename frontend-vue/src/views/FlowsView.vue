<script setup lang="ts">
/**
 * 库存流水页 — 全量可追溯
 * 过滤：单号 / 流水类型 / 库位
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { List, Download, Upload, TrendCharts } from '@element-plus/icons-vue'
import { getFlows, type FlowRow } from '@/api'
import SummaryCards, { GRADIENTS } from '@/components/SummaryCards.vue'

const FLOW_TYPE_OPTIONS = [
  { value: 'INBOUND', label: '入库收货' },
  { value: 'OUTBOUND', label: '出库发货' },
  { value: 'PICK_LOCK', label: '拣货锁定' },
  { value: 'MOVE_OUT', label: '移库出' },
  { value: 'MOVE_IN', label: '移库入' },
  { value: 'ADJUST_IN', label: '调整盘盈' },
  { value: 'ADJUST_OUT', label: '调整盘亏' },
]

// ============ 多维度汇总（Mock） ============
const summaryCards = [
  { label: '今日流水数', value: 1284, unit: '笔', icon: List, gradient: GRADIENTS.cyan },
  { label: '入库累计', value: 8640, unit: '件', icon: Download, gradient: GRADIENTS.indigo },
  { label: '出库累计', value: 7120, unit: '件', icon: Upload, gradient: GRADIENTS.green },
  { label: '本月流水总量', value: 38560, unit: '笔', icon: TrendCharts, gradient: GRADIENTS.purple },
]

const flows = ref<FlowRow[]>([])
const orderNo = ref('')
const flowType = ref('')
const locationCode = ref('')
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const loadFlows = async () => {
  loading.value = true
  try {
    const res = await getFlows({
      orderNo: orderNo.value || undefined,
      flowType: flowType.value || undefined,
      locationCode: locationCode.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    flows.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载流水失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const onSearch = () => {
  page.value = 1
  loadFlows()
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(loadFlows)
</script>

<template>
  <div>
    <!-- 多维度汇总 KPI（Mock） -->
    <SummaryCards :cards="summaryCards" />

    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <el-input v-model="orderNo" placeholder="单号" style="width: 220px" clearable @clear="onSearch" @keyup.enter="onSearch" />
      <el-select v-model="flowType" placeholder="流水类型" clearable style="width: 180px" @change="onSearch">
        <el-option v-for="o in FLOW_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-input v-model="locationCode" placeholder="库位编码" style="width: 180px" clearable @clear="onSearch" @keyup.enter="onSearch" />
      <el-button type="primary" @click="onSearch">查询</el-button>
    </div>

    <el-table :data="flows" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="流水类型" width="110">
        <template #default="{ row }">
          <el-tag :type="row.quantity > 0 ? 'success' : 'danger'" size="small">
            {{ FLOW_TYPE_OPTIONS.find(o => o.value === row.flowType)?.label || row.flowType }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="orderNo" label="单号" width="170" />
      <el-table-column prop="productName" label="商品" min-width="130" />
      <el-table-column prop="sku" label="SKU" width="120" />
      <el-table-column prop="locationCode" label="库位" width="110" />
      <el-table-column prop="batchNo" label="批次号" width="170" />
      <el-table-column label="变动量" width="100" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.quantity > 0 ? '#67c23a' : '#f56c6c', fontWeight: 700 }">
            {{ row.quantity > 0 ? '+' : '' }}{{ row.quantity }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="变动前→后" width="130" align="center">
        <template #default="{ row }">
          {{ row.beforeQty ?? '-' }} → {{ row.afterQty ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadFlows()"
      />
    </div>
  </div>
</template>
