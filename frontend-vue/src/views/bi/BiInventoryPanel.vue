<script setup lang="ts">
/**
 * BI 面板 · 库存分析（Inventory Analysis）
 * 数据源：generateBiData('inventory', state)（Mock）
 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import BiChart from '@/components/BiChart.vue'
import { useBiState } from '@/composables/useBiState'
import { generateBiData, BI_THEME } from '@/api/mock/bi'
import { biOption, axisCategory, axisValue } from './biChartTheme'

const { dataState } = useBiState()
const data = computed(() => generateBiData('inventory', dataState()))

const hBar = (
  rows: { name: string; v: number }[],
  color: string,
): EChartsOption =>
  biOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: axisValue(),
    yAxis: axisCategory([...rows].map((r) => r.name).reverse(), { inverse: false }),
    series: [{
      type: 'bar',
      data: [...rows].reverse().map((r) => r.v),
      barMaxWidth: 14,
      itemStyle: { color, borderRadius: [0, 6, 6, 0] },
    }],
  })

const topOption = computed(() => hBar(data.value.skuTop10.map((s) => ({ name: s.name, v: s.qty })), BI_THEME.blue))
const lowOption = computed(() => hBar(data.value.lowStockList.map((s) => ({ name: s.name, v: s.qty })), BI_THEME.red))

const ageOption = computed<EChartsOption>(() => ({
  color: data.value.ageDistribution.map((a) => a.color),
  tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}<br/>SKU数 ${p.value} · 占比 ${p.percent}%` },
  legend: { bottom: 0, icon: 'circle', textStyle: { color: BI_THEME.grey, fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['40%', '66%'], center: ['50%', '44%'],
    itemStyle: { borderColor: '#fff', borderWidth: 2 },
    data: data.value.ageDistribution.map((a) => ({ name: a.range, value: a.skuCount })),
  }],
}))

const batchOption = computed<EChartsOption>(() => {
  const rows = data.value.batchStatus
  const seg = (name: string, key: 'normal' | 'nearExpire' | 'expired' | 'frozen', color: string, radius?: number[]) => ({
    name, type: 'bar' as const, stack: 'b', barMaxWidth: 22, data: rows.map((r) => r[key]), itemStyle: { color, borderRadius: radius },
  })
  return biOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8, textStyle: { color: BI_THEME.grey, fontSize: 11 } },
    xAxis: axisCategory(rows.map((r) => r.name)),
    yAxis: axisValue(),
    series: [
      seg('正常', 'normal', BI_THEME.green),
      seg('临期', 'nearExpire', BI_THEME.orange),
      seg('已过期', 'expired', BI_THEME.red),
      seg('冻结', 'frozen', BI_THEME.grey, [4, 4, 0, 0]),
    ],
  })
})

const abcOption = computed<EChartsOption>(() => {
  const rows = data.value.abc
  return biOption({
    tooltip: {
      trigger: 'axis',
      formatter: (ps: any) => {
        const bar = ps[0]
        const line = ps[1]
        return `${bar.name}<br/>金额 ${bar.value.toLocaleString()}<br/>累计占比 ${Number(line.value).toFixed(1)}%`
      },
    },
    legend: { top: 0, right: 0, data: ['金额', '累计占比'], textStyle: { color: BI_THEME.grey, fontSize: 11 } },
    grid: { left: 8, right: 40, top: 34, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: rows.map((r) => r.sku), axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: BI_THEME.greyLight } } },
    yAxis: [
      axisValue({ name: '金额' }),
      axisValue({ name: '累计%', max: 100, splitLine: { show: false } }),
    ],
    series: [
      {
        name: '金额', type: 'bar', data: rows.map((r) => ({ value: r.amount, itemStyle: { color: r.category === 'A' ? BI_THEME.blue : r.category === 'B' ? BI_THEME.green : BI_THEME.grey } })),
        barMaxWidth: 20, markLine: { silent: true, symbol: 'none', lineStyle: { type: 'dashed', color: BI_THEME.grey }, data: [{ yAxis: 70, label: { formatter: 'A 70%' } }, { yAxis: 90, label: { formatter: 'B 90%' } }] },
      },
      { name: '累计占比', type: 'line', yAxisIndex: 1, smooth: true, data: rows.map((r) => r.cumulativePct), symbol: 'circle', symbolSize: 5, itemStyle: { color: BI_THEME.orange } },
    ],
  })
})
</script>

<template>
  <div class="bi-panel">
    <div class="bi-grid cols-2">
      <div class="bi-card"><h3>高库存 SKU TOP10 <span class="bi-sub">数量</span></h3><BiChart :option="topOption" height="320px" /></div>
      <div class="bi-card"><h3>低库存 SKU TOP10 <span class="bi-sub">需补货</span></h3><BiChart :option="lowOption" height="320px" /></div>
    </div>
    <div class="bi-grid cols-2 bi-section-gap">
      <div class="bi-card"><h3>库龄分布</h3><BiChart :option="ageOption" height="320px" /></div>
      <div class="bi-card"><h3>批次状态分布 <span class="bi-sub">按仓库</span></h3><BiChart :option="batchOption" height="320px" /></div>
    </div>
    <div class="bi-card bi-section-gap">
      <h3>ABC 分类帕累托 <span class="bi-sub">A 70% / B 20% / C 10%</span></h3>
      <BiChart :option="abcOption" height="360px" />
    </div>
  </div>
</template>
