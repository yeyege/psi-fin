<script setup lang="ts">
/**
 * BI 面板 · 作业效率（Efficiency）
 * 数据源：generateBiData('efficiency', state)（Mock，与 p0-2 解耦）
 * 员工柱点击下钻 → BiModal 展示个人 7 日明细
 */
import { computed, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import BiChart from '@/components/BiChart.vue'
import BiModal from '@/components/BiModal.vue'
import { useBiState } from '@/composables/useBiState'
import { generateBiData, BI_THEME } from '@/api/mock/bi'
import type { EfficiencyTask } from '@/api/mock/bi'
import { biOption, axisCategory, axisValue } from './biChartTheme'

const { dataState } = useBiState()
const data = computed(() => generateBiData('efficiency', dataState()))

/* ---- 员工日均拣货（点击下钻） ---- */
const workerOption = computed<EChartsOption>(() => {
  const rows = data.value.workerDaily
  return biOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 8, top: 30, bottom: 8, containLabel: true },
    xAxis: axisCategory(rows.map((r) => r.worker)),
    yAxis: axisValue({ name: '日均件' }),
    series: [{
      type: 'bar', barMaxWidth: 26,
      data: rows.map((r) => ({
        value: r.avg,
        itemStyle: { color: r.avg >= data.value.avgEff ? BI_THEME.blue : BI_THEME.greyLight, borderRadius: [6, 6, 0, 0] },
      })),
      markLine: {
        silent: true, symbol: 'none', lineStyle: { type: 'dashed', color: BI_THEME.orange },
        data: [{ yAxis: data.value.avgEff, label: { formatter: `均值 ${data.value.avgEff}`, color: BI_THEME.orange, fontSize: 11 } }],
      },
    }],
  })
})

const drillWorker = ref<string | null>(null)
const drillRow = computed(() => data.value.workerDaily.find((w) => w.worker === drillWorker.value) ?? null)
const onWorkerClick = (params: { name?: string }) => {
  if (params.name && data.value.workerDaily.some((w) => w.worker === params.name)) drillWorker.value = params.name
}
const drillOption = computed<EChartsOption>(() => {
  const w = drillRow.value
  if (!w) return biOption({})
  return biOption({
    tooltip: { trigger: 'axis' },
    xAxis: axisCategory(data.value.dayLabels),
    yAxis: axisValue(),
    series: [{ type: 'bar', barMaxWidth: 22, data: w.days, itemStyle: { color: BI_THEME.blue, borderRadius: [5, 5, 0, 0] } }],
  })
})

/* ---- 波次状态环形 ---- */
const waveOption = computed<EChartsOption>(() => biOption({
  tooltip: { trigger: 'item', formatter: '{b}: {c} 个 ({d}%)' },
  legend: { bottom: 0, icon: 'circle', textStyle: { color: BI_THEME.grey, fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['46%', '68%'], center: ['50%', '44%'],
    itemStyle: { borderColor: '#fff', borderWidth: 2 },
    label: { show: true, position: 'center', formatter: () => `{v|${data.value.wavePct}%}\n{l|完成率}`, rich: {
      v: { fontSize: 24, fontWeight: 700, color: '#1d1d1f', lineHeight: 30 },
      l: { fontSize: 11, color: BI_THEME.grey },
    } },
    emphasis: { label: { show: true } },
    data: data.value.waveStatus.map((x) => ({ name: x.name, value: x.value, itemStyle: { color: x.color } })),
  }],
}))

/* ---- 各环节耗时箱线（p10/p25/p50/p75/p90） ---- */
const durationOption = computed<EChartsOption>(() => {
  const rows = data.value.durationTypes
  return biOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>P10 ${p.value[1]} · P25 ${p.value[2]}<br/>中位 ${p.value[3]}<br/>P75 ${p.value[4]} · P90 ${p.value[5]} 分钟`,
    },
    grid: { left: 8, right: 8, top: 30, bottom: 8, containLabel: true },
    xAxis: axisCategory(rows.map((r) => r.type)),
    yAxis: axisValue({ name: '分钟' }),
    series: [{
      type: 'boxplot', boxWidth: [12, 30],
      itemStyle: { color: '#f5f5f7', borderColor: BI_THEME.blue, borderWidth: 1.5 },
      data: rows.map((r) => [r.p10, r.p25, r.p50, r.p75, r.p90]),
    }],
  })
})

/* ---- 实时任务流水（Tab 过滤） ---- */
type TaskFilter = 'all' | '进行中' | '已完成' | '异常'
const taskTab = ref<TaskFilter>('all')
const TASK_TABS: { key: TaskFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: '进行中', label: '进行中' },
  { key: '已完成', label: '已完成' },
  { key: '异常', label: '异常' },
]
const shownTasks = computed<EfficiencyTask[]>(() =>
  taskTab.value === 'all' ? data.value.tasks : data.value.tasks.filter((t) => t.status === taskTab.value),
)
const taskColor = (s: string) => (s === '已完成' ? BI_THEME.green : s === '异常' ? BI_THEME.red : s === '进行中' ? BI_THEME.blue : BI_THEME.grey)
</script>

<template>
  <div class="bi-panel">
    <div class="bi-grid cols-4">
      <div class="bi-card bi-kpi"><div class="label">人均日拣货</div><div class="value">{{ data.avgEff }}<span class="unit">件</span></div></div>
      <div class="bi-card bi-kpi"><div class="label">波次总数</div><div class="value">{{ data.waveTotal }}</div></div>
      <div class="bi-card bi-kpi"><div class="label">波次完成率</div><div class="value" :style="{ color: data.wavePct >= 60 ? BI_THEME.green : BI_THEME.orange }">{{ data.wavePct }}<span class="unit">%</span></div></div>
      <div class="bi-card bi-kpi"><div class="label">今日任务</div><div class="value">{{ data.taskTotal }}</div></div>
    </div>

    <div class="bi-grid cols-2 bi-section-gap">
      <div class="bi-card">
        <h3>员工日均拣货量 <span class="bi-sub">点击柱形下钻</span></h3>
        <BiChart :option="workerOption" height="300px" @chart-click="onWorkerClick" />
      </div>
      <div class="bi-card"><h3>波次状态分布</h3><BiChart :option="waveOption" height="300px" /></div>
    </div>

    <div class="bi-card bi-section-gap">
      <h3>各环节耗时分布 <span class="bi-sub">P10 - P90 箱线</span></h3>
      <BiChart :option="durationOption" height="280px" />
    </div>

    <div class="bi-card bi-section-gap">
      <h3>
        实时任务流水
        <span class="bi-tabs" style="margin-left:auto">
          <button v-for="t in TASK_TABS" :key="t.key" :class="{ active: taskTab === t.key }" @click="taskTab = t.key">{{ t.label }}</button>
        </span>
      </h3>
      <table class="bi-table">
        <thead><tr><th>任务号</th><th>类型</th><th>执行人</th><th>开始</th><th>进度</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-for="t in shownTasks" :key="t.no">
            <td class="mono">{{ t.no }}</td>
            <td>{{ t.type }}</td>
            <td>{{ t.worker }}</td>
            <td>{{ t.startTime }}</td>
            <td style="min-width:120px">
              <div class="bi-meter"><i :style="{ width: t.progress + '%', background: taskColor(t.status) }"></i></div>
              <span class="bi-sub" style="margin-left:6px">{{ t.progress }}%</span>
            </td>
            <td><span class="bi-tag" :style="{ color: taskColor(t.status), borderColor: taskColor(t.status) }">{{ t.status }}</span></td>
          </tr>
          <tr v-if="!shownTasks.length"><td colspan="6" style="text-align:center;color:#86868b;padding:24px">暂无该状态任务</td></tr>
        </tbody>
      </table>
    </div>

    <BiModal :visible="!!drillRow" :title="`${drillRow?.worker ?? ''} · 近 7 日拣货明细`" @close="drillWorker = null">
      <div v-if="drillRow">
        <p class="bi-sub" style="margin:0 0 12px">日均 {{ drillRow.avg }} 件 · 峰值 {{ Math.max(...drillRow.days) }} 件 · 谷值 {{ Math.min(...drillRow.days) }} 件</p>
        <BiChart :option="drillOption" height="240px" />
      </div>
    </BiModal>
  </div>
</template>

<style scoped>
.bi-card h3 { display: flex; align-items: center; }
.mono { font-variant-numeric: tabular-nums; }
.bi-tag { border: 1px solid currentColor; border-radius: 999px; padding: 1px 8px; font-size: 11px; }
</style>
