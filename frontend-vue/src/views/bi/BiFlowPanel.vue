<script setup lang="ts">
/**
 * BI 面板 · 出入库分析（Flow Analysis）
 * 数据源：generateBiData('flow', state)（Mock）
 */
import { computed, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import BiChart from '@/components/BiChart.vue'
import { useBiState } from '@/composables/useBiState'
import { generateBiData, BI_THEME } from '@/api/mock/bi'
import { biOption, axisCategory, axisValue } from './biChartTheme'

const { dataState } = useBiState()
const data = computed(() => generateBiData('flow', dataState()))

const metric = ref<'qty' | 'amt'>('qty')
const amtFmt = (v: number) => (v >= 1e8 ? (v / 1e8).toFixed(2) + '亿' : v >= 1e4 ? (v / 1e4).toFixed(1) + '万' : String(v))

const trendOption = computed<EChartsOption>(() => {
  const t = data.value.trend30
  const inS = metric.value === 'qty' ? t.inQty : t.inAmt
  const outS = metric.value === 'qty' ? t.outQty : t.outAmt
  return biOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => (metric.value === 'amt' ? '¥' + amtFmt(Number(v)) : String(v)) },
    legend: { top: 0, right: 0, data: ['入库', '出库'], textStyle: { color: BI_THEME.grey, fontSize: 11 } },
    grid: { left: 8, right: 18, top: 34, bottom: 52, containLabel: true },
    xAxis: axisCategory(t.labels),
    yAxis: axisValue(),
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
    series: [
      { name: '入库', type: 'line', smooth: true, showSymbol: false, data: inS, itemStyle: { color: BI_THEME.blue }, areaStyle: { opacity: 0.1 } },
      { name: '出库', type: 'line', smooth: true, showSymbol: false, data: outS, itemStyle: { color: BI_THEME.green }, areaStyle: { opacity: 0.1 } },
    ],
  })
})

const returnTrendOption = computed<EChartsOption>(() => {
  const r = data.value.returnTrend
  return biOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => (Number(v) * 100).toFixed(2) + '%' },
    xAxis: axisCategory(r.labels),
    yAxis: axisValue({ axisLabel: { color: BI_THEME.grey, fontSize: 11, formatter: (v: number) => (v * 100).toFixed(0) + '%' } }),
    series: [{ name: '退货率', type: 'line', smooth: true, data: r.values, itemStyle: { color: BI_THEME.red }, areaStyle: { opacity: 0.08 } }],
  })
})

const reasonOption = computed<EChartsOption>(() => biOption({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, icon: 'circle', textStyle: { color: BI_THEME.grey, fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['42%', '66%'], center: ['50%', '42%'], itemStyle: { borderColor: '#fff', borderWidth: 2 },
    data: data.value.returnReasons.map((x) => ({ name: x.name, value: x.count, itemStyle: { color: x.color } })),
  }],
}))

const rateColor = (r: number, good: number, bad: number, invert = false) => {
  const ok = invert ? r < good : r > good
  const badHit = invert ? r > bad : r < bad
  return ok ? BI_THEME.green : badHit ? BI_THEME.red : BI_THEME.orange
}
const netPositive = computed(() => data.value.netVal >= 0)
const overReturn = computed(() => data.value.avgRetRate > 0.05)
</script>

<template>
  <div class="bi-panel">
    <div class="bi-card">
      <h3>
        30 天出入库趋势
        <span class="bi-seg" style="margin-left:auto">
          <button :class="{ active: metric === 'qty' }" @click="metric = 'qty'">数量</button>
          <button :class="{ active: metric === 'amt' }" @click="metric = 'amt'">金额</button>
        </span>
      </h3>
      <BiChart :option="trendOption" height="340px" />
    </div>

    <div class="bi-grid cols-3 bi-section-gap">
      <div class="bi-card bi-gauge">
        <div><div class="g-label">入库合计</div><div class="g-val">{{ data.netIn.toLocaleString() }}</div></div>
        <div class="g-net"><div class="g-label">净增减</div><div class="g-val" :class="netPositive ? 'g-pos' : 'g-neg'">{{ netPositive ? '+' : '' }}{{ data.netVal.toLocaleString() }}</div></div>
        <div><div class="g-label">出库合计</div><div class="g-val">{{ data.netOut.toLocaleString() }}</div></div>
      </div>
      <div class="bi-card" style="grid-column:span 2"><h3>退货原因分布 <span class="bi-sub">近 14 天</span></h3><BiChart :option="reasonOption" height="220px" /></div>
    </div>

    <div v-if="overReturn" class="bi-warn bi-section-gap">⚠ 总体退货率 {{ (data.avgRetRate * 100).toFixed(2) }}% 超过 5% 警戒线，建议排查质量与错发问题</div>

    <div class="bi-grid cols-2 bi-section-gap">
      <div class="bi-card">
        <h3>供应商入库 TOP10 <span class="bi-sub">金额 / 准时率</span></h3>
        <div v-for="(v, i) in data.vendors" :key="v.vendor" class="bi-rank">
          <span class="idx" :class="{ top: i < 3 }">{{ i + 1 }}</span>
          <span class="name">{{ v.vendor }}</span>
          <span class="val">¥{{ amtFmt(v.amount) }}</span>
          <div class="bi-meter"><i :style="{ width: v.onTimeRate * 100 + '%', background: rateColor(v.onTimeRate, 0.95, 0.8) }"></i></div>
          <span style="width:44px;text-align:right;font-size:12px;color:#86868b">{{ (v.onTimeRate * 100).toFixed(0) }}%</span>
        </div>
      </div>
      <div class="bi-card">
        <h3>客户出库 TOP10 <span class="bi-sub">金额 / 退货率</span></h3>
        <div v-for="(c, i) in data.customers" :key="c.customer" class="bi-rank">
          <span class="idx" :class="{ top: i < 3 }">{{ i + 1 }}</span>
          <span class="name">{{ c.customer }}</span>
          <span class="val">¥{{ amtFmt(c.amount) }}</span>
          <div class="bi-meter"><i :style="{ width: Math.min(100, c.returnRate * 100 * 4) + '%', background: rateColor(c.returnRate, 0.03, 0.1, true) }"></i></div>
          <span style="width:44px;text-align:right;font-size:12px;color:#86868b">{{ (c.returnRate * 100).toFixed(1) }}%</span>
        </div>
      </div>
    </div>

    <div class="bi-card bi-section-gap">
      <h3>退货率趋势 <span class="bi-sub">近 14 天</span></h3>
      <BiChart :option="returnTrendOption" height="260px" />
    </div>
  </div>
</template>

<style scoped>
.bi-card h3 { display: flex; align-items: center; }
.bi-gauge { display: flex; }
</style>
