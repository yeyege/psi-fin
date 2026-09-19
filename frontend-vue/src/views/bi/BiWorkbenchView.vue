<script setup lang="ts">
/**
 * BI 工作台外壳：Apple 风格顶栏（时间/仓库筛选 + 导出）+ Dock 五面板切换。
 * 数据总览/库存分析/出入库分析/作业效率 为 Mock 面板；经营财务走真实接口。
 */
import { ref, computed, markRaw, type Component } from 'vue'
import { WH_LIST } from '@/api/mock/bi'
import type { BiPreset } from '@/api/mock/bi'
import { useBiState, BI_PANELS, type BiPanelKey } from '@/composables/useBiState'
import { exportPanelCharts } from './biChartTheme'
import BiOverviewPanel from './BiOverviewPanel.vue'
import BiInventoryPanel from './BiInventoryPanel.vue'
import BiFlowPanel from './BiFlowPanel.vue'
import BiEfficiencyPanel from './BiEfficiencyPanel.vue'
import BiFinancePanel from './BiFinancePanel.vue'
import '@/styles/bi-apple.css'

const { state, setPreset, setCustomRange, setPanel, toggleWarehouse } = useBiState()

const PRESETS: { key: BiPreset; label: string }[] = [
  { key: 'today', label: '今天' },
  { key: '7d', label: '近 7 天' },
  { key: '30d', label: '近 30 天' },
  { key: 'custom', label: '自定义' },
]

const PANEL_COMPONENTS: Record<BiPanelKey, Component> = {
  overview: markRaw(BiOverviewPanel),
  inventory: markRaw(BiInventoryPanel),
  flow: markRaw(BiFlowPanel),
  efficiency: markRaw(BiEfficiencyPanel),
  finance: markRaw(BiFinancePanel),
}
const currentPanel = computed(() => PANEL_COMPONENTS[state.activePanel])
const currentLabel = computed(() => BI_PANELS.find((p) => p.key === state.activePanel)?.label ?? '')

/* 自定义区间：本地绑定 → 校验后落入全局 state */
const dateErr = ref('')
const onDateChange = () => {
  const { start, end } = custom.value
  if (!start || !end) { dateErr.value = ''; return }
  if (start > end) { dateErr.value = '开始日期不能晚于结束日期'; return }
  dateErr.value = ''
  setCustomRange(start, end)
}
const custom = ref({ start: state.time.start ?? '', end: state.time.end ?? '' })

const containerRef = ref<HTMLElement | null>(null)
const doExport = () => exportPanelCharts(containerRef.value, currentLabel.value)
</script>

<template>
  <div class="bi-scope">
    <!-- 顶栏 -->
    <div class="bi-topbar">
      <div class="bi-title">
        业财数据工作台
        <small>{{ currentLabel }}</small>
        <span class="bi-mock-flag" title="除「经营财务」外均为可复现 Mock 数据，用于演示">演示数据</span>
      </div>
      <div class="bi-filters">
        <div class="bi-seg">
          <button
            v-for="p in PRESETS" :key="p.key"
            :class="{ active: state.time.preset === p.key }"
            @click="setPreset(p.key)"
          >{{ p.label }}</button>
        </div>
        <div v-if="state.time.preset === 'custom'" class="bi-date">
          <input v-model="custom.start" type="date" @change="onDateChange" />
          <span>至</span>
          <input v-model="custom.end" type="date" @change="onDateChange" />
          <span v-if="dateErr" class="bi-date-err">{{ dateErr }}</span>
        </div>
        <div class="bi-chips">
          <button class="bi-chip" :class="{ active: state.warehouses.includes('all') }" @click="toggleWarehouse('all')">全部仓库</button>
          <button
            v-for="w in WH_LIST" :key="w.id"
            class="bi-chip" :class="{ active: state.warehouses.includes(w.id) }"
            @click="toggleWarehouse(w.id)"
          >{{ w.name }}</button>
        </div>
        <button class="bi-export" title="将当前面板图表导出为 PNG" @click="doExport">导出图表</button>
      </div>
    </div>

    <!-- Dock 面板切换 -->
    <div class="bi-dock">
      <button
        v-for="p in BI_PANELS" :key="p.key"
        :class="{ active: state.activePanel === p.key }"
        @click="setPanel(p.key)"
      >{{ p.label }}</button>
    </div>

    <!-- 面板区 -->
    <div ref="containerRef">
      <KeepAlive>
        <component :is="currentPanel" :key="state.activePanel" />
      </KeepAlive>
    </div>
  </div>
</template>
