<script setup lang="ts">
/**
 * 统一 ECharts 容器：init / setOption / resize / dispose 一处收敛，
 * 消除各视图重复的命令式图表样板；对外暴露导出图片与获取实例能力。
 */
import { ref, shallowRef, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  option: EChartsOption
  height?: string
}>()

const emit = defineEmits<{
  (e: 'chart-click', params: { name?: string; dataIndex?: number; seriesName?: string; value?: unknown }): void
}>()

const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let ro: ResizeObserver | null = null

const apply = () => {
  if (chart.value) chart.value.setOption(props.option, true)
}

onMounted(async () => {
  await nextTick()
  if (!el.value) return
  chart.value = echarts.init(el.value)
  chart.value.setOption(props.option, true)
  chart.value.on('click', (params) => emit('chart-click', params as never))
  ro = new ResizeObserver(() => chart.value?.resize())
  ro.observe(el.value)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  chart.value?.dispose()
  chart.value = null
})

watch(() => props.option, apply, { deep: true })

defineExpose({
  getDataURL: (backgroundColor = '#fff') =>
    chart.value?.getDataURL({ pixelRatio: 2, backgroundColor }) ?? '',
  getInstance: () => chart.value,
})
</script>

<template>
  <div ref="el" class="bi-chart" :style="{ height: height || '320px', width: '100%' }"></div>
</template>

<style scoped>
.bi-chart { min-height: 120px; }
</style>
