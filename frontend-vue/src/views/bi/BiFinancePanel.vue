<script setup lang="ts">
/**
 * BI 面板 · 经营财务（Finance）
 * 数据源仍为真实接口 /api/executive/*（与财务页同口径），仅呈现层 Apple 化。
 * 接口失败时静默降级为空态，不影响其他 Mock 面板。
 */
import { ref, computed, onMounted } from 'vue'
import type { EChartsOption } from 'echarts'
import BiChart from '@/components/BiChart.vue'
import {
  getExecutiveSummary, getReceivableTop, getAgingDistribution, getExecutiveTrends,
  type ExecutiveSummary, type ReceivableTopRow, type AgingDistribution, type TrendPoint,
} from '@/api'
import { BI_THEME } from '@/api/mock/bi'
import { biOption, axisCategory, axisValue } from './biChartTheme'

const summary = ref<ExecutiveSummary | null>(null)
const topRows = ref<ReceivableTopRow[]>([])
const aging = ref<AgingDistribution | null>(null)
const trend = ref<TrendPoint[]>([])
const loading = ref(true)
const failed = ref(false)

const money = (n: number) => `¥${(n || 0).toFixed(2)}`
const amtFmt = (v: number) => (v >= 1e8 ? (v / 1e8).toFixed(2) + '亿' : v >= 1e4 ? (v / 1e4).toFixed(1) + '万' : v.toFixed(0))

const agingOption = computed<EChartsOption>(() => {
  const d = aging.value
  if (!d) return biOption({})
  return biOption({
    tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}<br/>¥${amtFmt(p.value)} (${p.percent}%)` },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: BI_THEME.grey, fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['42%', '66%'], center: ['50%', '44%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11, color: BI_THEME.grey },
      data: [
        { name: '未到期', value: d.notDue, itemStyle: { color: BI_THEME.green } },
        { name: '逾期1-30天', value: d.days1to30, itemStyle: { color: BI_THEME.orange } },
        { name: '逾期31-60天', value: d.days31to60, itemStyle: { color: BI_THEME.red } },
        { name: '逾期60天以上', value: d.days60plus, itemStyle: { color: '#c03639' } },
      ],
    }],
  })
})

const topOption = computed<EChartsOption>(() => {
  const rows = [...topRows.value].reverse()
  return biOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: any) => `${p[0].name}<br/>未结余额 ¥${amtFmt(p[0].value)}` },
    grid: { left: 8, right: 30, top: 12, bottom: 8, containLabel: true },
    xAxis: axisValue({ axisLabel: { color: BI_THEME.grey, fontSize: 11, formatter: (v: number) => amtFmt(v) } }),
    yAxis: axisCategory(rows.map((r) => r.partnerName)),
    series: [{ type: 'bar', data: rows.map((r) => r.balance), barMaxWidth: 16, itemStyle: { color: BI_THEME.blue, borderRadius: [0, 6, 6, 0] } }],
  })
})

const trendOption = computed<EChartsOption>(() => {
  const pts = trend.value
  return biOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => '¥' + amtFmt(Number(v)) },
    legend: { top: 0, right: 0, data: ['订单金额', '回款金额'], textStyle: { color: BI_THEME.grey, fontSize: 11 } },
    grid: { left: 8, right: 18, top: 34, bottom: 8, containLabel: true },
    xAxis: axisCategory(pts.map((p) => p.date.slice(5))),
    yAxis: axisValue({ axisLabel: { color: BI_THEME.grey, fontSize: 11, formatter: (v: number) => amtFmt(v) } }),
    series: [
      { name: '订单金额', type: 'line', smooth: true, showSymbol: false, data: pts.map((p) => p.orderAmount), itemStyle: { color: BI_THEME.blue }, areaStyle: { opacity: 0.1 } },
      { name: '回款金额', type: 'line', smooth: true, showSymbol: false, data: pts.map((p) => p.receiptAmount), itemStyle: { color: BI_THEME.green }, areaStyle: { opacity: 0.1 } },
    ],
  })
})

onMounted(async () => {
  try {
    const [s, top, dist, tr] = await Promise.all([
      getExecutiveSummary(), getReceivableTop(5), getAgingDistribution(), getExecutiveTrends(30),
    ])
    summary.value = s.data
    topRows.value = top.data
    aging.value = dist.data
    trend.value = tr.data
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
})

const kpis = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: '应收总额', value: money(s.receivableTotal), color: BI_THEME.blue },
    { label: '已回款', value: money(s.receivedTotal), color: BI_THEME.green },
    { label: '未回款', value: money(s.outstandingTotal), color: BI_THEME.orange },
    { label: '逾期金额', value: money(s.overdueTotal), color: BI_THEME.red },
  ]
})
</script>

<template>
  <div class="bi-panel">
    <div v-if="loading" class="bi-loading">经营数据加载中…</div>
    <div v-else-if="failed" class="bi-warn">⚠ 经营财务数据来自真实接口，当前后端不可用（Mock 演示模式下仅此面板受限，其余面板不受影响）</div>
    <template v-else>
      <div class="bi-grid cols-4">
        <div v-for="k in kpis" :key="k.label" class="bi-card bi-kpi">
          <div class="label">{{ k.label }}</div>
          <div class="value" :style="{ color: k.color }">{{ k.value }}</div>
        </div>
      </div>

      <div class="bi-grid cols-2 bi-section-gap">
        <div class="bi-card"><h3>账龄分布 <span class="bi-sub">未结应收</span></h3><BiChart :option="agingOption" height="320px" /></div>
        <div class="bi-card"><h3>应收余额 TOP 客户</h3><BiChart :option="topOption" height="320px" /></div>
      </div>

      <div class="bi-card bi-section-gap">
        <h3>订单 / 回款趋势 <span class="bi-sub">近 30 天</span></h3>
        <BiChart :option="trendOption" height="320px" />
      </div>

      <div v-if="summary" class="bi-card bi-section-gap">
        <h3>经营概览 <span class="bi-sub">与财务页同口径</span></h3>
        <div class="bi-desc-grid">
          <div><span>销售订单数</span><b>{{ summary.orderCount }}</b></div>
          <div><span>订单总金额</span><b>¥{{ summary.orderAmount.toFixed(2) }}</b></div>
          <div><span>应收总额</span><b>¥{{ summary.receivableTotal.toFixed(2) }}</b></div>
          <div><span>已回款</span><b>¥{{ summary.receivedTotal.toFixed(2) }}</b></div>
          <div><span>未回款</span><b>¥{{ summary.outstandingTotal.toFixed(2) }}</b></div>
          <div><span>逾期金额</span><b style="color:#ff3b30">¥{{ summary.overdueTotal.toFixed(2) }}</b></div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.bi-card h3 { display: flex; align-items: center; }
.bi-desc-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px 24px; }
.bi-desc-grid > div { display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f2; padding: 8px 2px; font-size: 13px; }
.bi-desc-grid span { color: #86868b; }
.bi-desc-grid b { font-variant-numeric: tabular-nums; font-weight: 600; }
</style>
