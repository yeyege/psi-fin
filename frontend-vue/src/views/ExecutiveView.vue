<script setup lang="ts">
/**
 * 经营驾驶舱 — 业财一体的决策层
 * 指标与图表全部来自销售订单 + 财务流水,与财务页同口径
 */
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Coin, Wallet, Warning, DataLine } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getExecutiveSummary, getReceivableTop, getAgingDistribution, getExecutiveTrends,
  type ExecutiveSummary, type ReceivableTopRow, type AgingDistribution, type TrendPoint,
} from '@/api'
import SummaryCards, { GRADIENTS, type SummaryCard } from '@/components/SummaryCards.vue'

const summary = ref<ExecutiveSummary | null>(null)
const summaryCards = ref<SummaryCard[]>([])

const agingRef = ref<HTMLDivElement | null>(null)
const topRef = ref<HTMLDivElement | null>(null)
const trendRef = ref<HTMLDivElement | null>(null)
let agingChart: echarts.ECharts | null = null
let topChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

const money = (n: number) => `¥${(n || 0).toFixed(2)}`

const loadSummary = async () => {
  const res = await getExecutiveSummary()
  summary.value = res.data
  const s = res.data
  summaryCards.value = [
    { label: '应收总额', value: money(s.receivableTotal), unit: '', icon: Coin, gradient: GRADIENTS.blue },
    { label: '已回款', value: money(s.receivedTotal), unit: '', icon: Wallet, gradient: GRADIENTS.green },
    { label: '未回款', value: money(s.outstandingTotal), unit: '', icon: DataLine, gradient: GRADIENTS.orange },
    { label: '逾期金额', value: money(s.overdueTotal), unit: '', icon: Warning, gradient: GRADIENTS.red },
  ]
}

const renderAging = async (dist: AgingDistribution) => {
  if (!agingRef.value) return
  agingChart = agingChart || echarts.init(agingRef.value)
  const data = [
    { name: '未到期', value: dist.notDue },
    { name: '逾期1-30天', value: dist.days1to30 },
    { name: '逾期31-60天', value: dist.days31to60 },
    { name: '逾期60天以上', value: dist.days60plus },
  ]
  agingChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    color: ['#67c23a', '#e6a23c', '#f56c6c', '#c03639'],
    series: [{ type: 'pie', radius: ['38%', '62%'], center: ['50%', '45%'], data, label: { formatter: '{b}\n{d}%' } }],
  })
}

const renderTop = async (rows: ReceivableTopRow[]) => {
  if (!topRef.value) return
  topChart = topChart || echarts.init(topRef.value)
  const names = rows.map((r) => r.partnerName).reverse()
  const values = rows.map((r) => r.balance).reverse()
  topChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: any) => `${p[0].name}<br/>未结余额: ¥${Number(p[0].value).toFixed(2)}` },
    grid: { left: 10, right: 30, top: 20, bottom: 10, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: (v: number) => `¥${v}` } },
    yAxis: { type: 'category', data: names },
    series: [{ type: 'bar', data: values, barWidth: 16, itemStyle: { color: '#409eff', borderRadius: [0, 6, 6, 0] } }],
  })
}

const renderTrend = async (points: TrendPoint[]) => {
  if (!trendRef.value) return
  trendChart = trendChart || echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['订单金额', '回款金额'], top: 0 },
    grid: { left: 10, right: 20, top: 40, bottom: 10, containLabel: true },
    xAxis: { type: 'category', data: points.map((p) => p.date.slice(5)) },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => `¥${v}` } },
    series: [
      { name: '订单金额', type: 'line', smooth: true, data: points.map((p) => p.orderAmount), areaStyle: { opacity: 0.12 }, itemStyle: { color: '#409eff' } },
      { name: '回款金额', type: 'line', smooth: true, data: points.map((p) => p.receiptAmount), areaStyle: { opacity: 0.12 }, itemStyle: { color: '#67c23a' } },
    ],
  })
}

const loadCharts = async () => {
  const [top, dist, trend] = await Promise.all([
    getReceivableTop(5), getAgingDistribution(), getExecutiveTrends(30),
  ])
  await nextTick()
  renderAging(dist.data)
  renderTop(top.data)
  renderTrend(trend.data)
}

const handleResize = () => {
  agingChart?.resize(); topChart?.resize(); trendChart?.resize()
}

onMounted(async () => {
  try {
    await loadSummary()
    await loadCharts()
  } catch (e: any) {
    ElMessage.error('驾驶舱加载失败: ' + (e.response?.data?.detail || e.message))
  }
  window.addEventListener('resize', handleResize)
  setTimeout(handleResize, 300)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  agingChart?.dispose(); topChart?.dispose(); trendChart?.dispose()
  agingChart = topChart = trendChart = null
})
</script>

<template>
  <div>
    <SummaryCards :cards="summaryCards" />

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card shadow="never" header="账龄分布（未结应收）">
          <div ref="agingRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" header="应收余额 TOP 客户">
          <div ref="topRef" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" header="订单金额 / 回款金额趋势（近 30 天）" style="margin-top: 16px">
      <div ref="trendRef" style="height: 340px"></div>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>经营概览（与财务页同口径）</template>
      <el-descriptions v-if="summary" :column="3" border>
        <el-descriptions-item label="销售订单数">{{ summary.orderCount }}</el-descriptions-item>
        <el-descriptions-item label="订单总金额">¥{{ summary.orderAmount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="应收总额">¥{{ summary.receivableTotal.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="已回款">¥{{ summary.receivedTotal.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="未回款">¥{{ summary.outstandingTotal.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="逾期金额">
          <span style="color: #f56c6c">¥{{ summary.overdueTotal.toFixed(2) }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>
