<script setup lang="ts">
/**
 * BI 面板 · 数据总览（Overview）
 * 数据源：generateBiData('overview', state)（Mock，零网络）
 */
import { computed, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import BiChart from '@/components/BiChart.vue'
import BiModal from '@/components/BiModal.vue'
import { useBiState } from '@/composables/useBiState'
import { generateBiData, BI_THEME, type OverviewAlert } from '@/api/mock/bi'
import { biOption, axisCategory, axisValue } from './biChartTheme'

const { dataState, setPanel } = useBiState()
const data = computed(() => generateBiData('overview', dataState()))

const trendOption = computed<EChartsOption>(() => {
  const t = data.value.trend
  return biOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'], right: 0, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8, textStyle: { color: BI_THEME.grey, fontSize: 12 } },
    xAxis: axisCategory(t.labels),
    yAxis: axisValue(),
    series: [
      { name: '入库', type: 'bar', data: t.inbound, barMaxWidth: 18, itemStyle: { color: BI_THEME.blue, borderRadius: [4, 4, 0, 0] } },
      { name: '出库', type: 'bar', data: t.outbound, barMaxWidth: 18, itemStyle: { color: BI_THEME.green, borderRadius: [4, 4, 0, 0] } },
    ],
  })
})

const orderStatusOption = computed<EChartsOption>(() => {
  const total = data.value.orderStatus.reduce((s, x) => s + x.value, 0)
  return biOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: BI_THEME.grey, fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['46%', '68%'], center: ['50%', '44%'], avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: true, position: 'center', formatter: () => `{v|${total}}\n{n|总单据}`, rich: { v: { fontSize: 24, fontWeight: 700, color: '#1d1d1f' }, n: { fontSize: 12, color: BI_THEME.grey } } } as never,
      emphasis: { label: { show: true, formatter: '{b}\n{c}' } },
      data: data.value.orderStatus.map((x) => ({ name: x.name, value: x.value, itemStyle: { color: x.color } })),
    }],
  })
})

const whInvOption = computed<EChartsOption>(() => {
  const rows = data.value.whInventory
  const names = rows.map((r) => r.name)
  return biOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['可用', '锁定'], right: 0, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8, textStyle: { color: BI_THEME.grey, fontSize: 12 } },
    xAxis: axisValue(),
    yAxis: axisCategory(names, { inverse: true }),
    series: [
      { name: '可用', type: 'bar', stack: 'w', data: rows.map((r) => r.available), barMaxWidth: 16, itemStyle: { color: BI_THEME.blue, borderRadius: [4, 0, 0, 4] } },
      { name: '锁定', type: 'bar', stack: 'w', data: rows.map((r) => r.locked), barMaxWidth: 16, itemStyle: { color: BI_THEME.orange } },
    ],
  })
})

// 预警下钻 Modal
const activeAlert = ref<OverviewAlert | null>(null)
const alertOpen = computed({ get: () => !!activeAlert.value, set: (v: boolean) => { if (!v) activeAlert.value = null } })
const alertSpark = computed(() => {
  const base = activeAlert.value?.current ?? 5
  return Array.from({ length: 7 }, (_, i) => Math.max(1, Math.round(base * (0.6 + 0.5 * Math.sin(i + base)))))
})
const openAlert = (a: OverviewAlert) => { activeAlert.value = a }
</script>

<template>
  <div class="bi-panel">
    <!-- KPI 卡 -->
    <div class="bi-grid cols-4">
      <div v-for="k in data.kpis" :key="k.label" class="bi-card bi-kpi">
        <div class="label">{{ k.label }}</div>
        <template v-if="k.rows">
          <div class="bi-kpi-rows">
            <div v-for="r in k.rows" :key="r.name" class="bi-kpi-row">
              {{ r.name }} {{ r.done }} / {{ r.plan }}
              <div class="bar"><i :style="{ width: Math.min(100, (r.done / r.plan) * 100) + '%', background: r.name === '入库' ? BI_THEME.blue : BI_THEME.green }"></i></div>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="value">{{ k.value }}<span class="unit">{{ k.unit }}</span></div>
          <div v-if="k.progress != null" class="bi-progress"><i :style="{ width: k.progress + '%' }"></i></div>
          <div v-if="k.trend" class="badge" :class="k.trend">
            {{ k.trend === 'up' ? '▲' : '▼' }} {{ k.trendVal }}%
          </div>
        </template>
        <div v-if="k.sub" class="sub">{{ k.sub }}</div>
      </div>
    </div>

    <!-- 彩色统计卡 -->
    <div class="bi-grid cols-4 bi-section-gap">
      <div
        v-for="s in data.stats"
        :key="s.label"
        class="bi-stat"
        :class="{ clickable: !!s.type }"
        :style="{ background: `linear-gradient(135deg, ${s.gradient[0]}, ${s.gradient[1]})` }"
        @click="s.type && setPanel('flow')"
      >
        <div class="label">{{ s.label }}</div>
        <div class="value">{{ s.value }}</div>
      </div>
    </div>

    <!-- 趋势 + 单据状态 -->
    <div class="bi-grid cols-2 bi-section-gap">
      <div class="bi-card"><h3>出入库趋势 <span class="bi-sub">按筛选范围</span></h3><BiChart :option="trendOption" height="300px" /></div>
      <div class="bi-card"><h3>单据状态分布</h3><BiChart :option="orderStatusOption" height="300px" /></div>
    </div>

    <!-- 仓库分布 + 预警 -->
    <div class="bi-grid cols-2 bi-section-gap">
      <div class="bi-card"><h3>各仓库库存分布</h3><BiChart :option="whInvOption" height="300px" /></div>
      <div class="bi-card">
        <h3>库存预警 <span class="bi-sub">点击下钻</span></h3>
        <div v-for="(a, i) in data.alerts" :key="i" class="bi-alert" @click="openAlert(a)">
          <span class="bi-tag" :class="a.level">{{ a.tag }}</span>
          <div>
            <div class="a-title">{{ a.title }}</div>
            <div class="a-meta">{{ a.sku }} · {{ a.warehouse }}</div>
          </div>
          <div class="a-right">
            现 {{ a.current }} / 阈 {{ a.threshold }}
            <div v-if="a.daysLeft">剩 {{ a.daysLeft }} 天</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 待办网格 -->
    <div class="bi-card bi-section-gap">
      <h3>待办事项</h3>
      <div class="bi-grid cols-4">
        <div v-for="(t, i) in data.todos" :key="i" class="bi-todo">
          <div class="t-head">
            <span class="t-tag" :style="{ background: t.color }">{{ t.tagText }}</span>
            <span class="t-time">{{ t.time }}</span>
          </div>
          <div class="t-title">{{ t.title }}</div>
          <div class="t-desc">{{ t.desc }}</div>
        </div>
      </div>
    </div>

    <!-- 预警下钻 Modal -->
    <BiModal v-model:visible="alertOpen" :title="activeAlert ? `${activeAlert.title} · SKU 明细` : ''">
      <div v-if="activeAlert">
        <p style="font-size:13px;color:#86868b;margin:0 0 12px">{{ activeAlert.sku }} · {{ activeAlert.warehouse }} · 当前 {{ activeAlert.current }} 件 / 阈值 {{ activeAlert.threshold }} 件</p>
        <h3 style="font-size:14px;margin:0 0 8px">近 7 天出入库</h3>
        <div class="bi-spark"><i v-for="(v, i) in alertSpark" :key="i" :style="{ height: (v / Math.max(...alertSpark)) * 100 + '%' }"></i></div>
        <h3 style="font-size:14px;margin:16px 0 8px">各仓库分布</h3>
        <table class="bi-table">
          <thead><tr><th>仓库</th><th>可用</th><th>锁定</th></tr></thead>
          <tbody>
            <tr v-for="w in data.whInventory" :key="w.name"><td>{{ w.name }}</td><td>{{ w.available }}</td><td>{{ w.locked }}</td></tr>
          </tbody>
        </table>
      </div>
    </BiModal>
  </div>
</template>

<style scoped>
.bi-stat { cursor: default; }
</style>
