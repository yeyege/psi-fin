/**
 * BI 工作台全局筛选/面板状态（模块级单例，顶栏与各面板共享）
 * 时间范围 + 仓库 + 当前面板；数据由各面板 computed 依据本状态派生。
 */
import { reactive, readonly } from 'vue'
import type { BiPreset, BiState } from '@/api/mock/bi'

export type BiPanelKey = 'overview' | 'inventory' | 'flow' | 'efficiency' | 'finance'

export const BI_PANELS: { key: BiPanelKey; label: string }[] = [
  { key: 'overview', label: '数据总览' },
  { key: 'inventory', label: '库存分析' },
  { key: 'flow', label: '出入库分析' },
  { key: 'efficiency', label: '作业效率' },
  { key: 'finance', label: '经营财务' },
]

interface BiUiState extends BiState {
  activePanel: BiPanelKey
}

const state = reactive<BiUiState>({
  time: { preset: '7d', start: null, end: null },
  warehouses: ['all'],
  activePanel: 'overview',
})

export function useBiState() {
  const setPreset = (preset: BiPreset) => {
    state.time.preset = preset
    if (preset !== 'custom') { state.time.start = null; state.time.end = null }
  }
  const setCustomRange = (start: string | null, end: string | null) => {
    state.time.preset = 'custom'
    state.time.start = start
    state.time.end = end
  }
  const setPanel = (panel: BiPanelKey) => { state.activePanel = panel }

  /** 仓库多选：含 'all' 语义；选中具体仓会移除 'all'，反之亦然 */
  const toggleWarehouse = (id: string) => {
    if (id === 'all') { state.warehouses = ['all']; return }
    const set = new Set(state.warehouses.filter((w) => w !== 'all'))
    set.has(id) ? set.delete(id) : set.add(id)
    state.warehouses = set.size ? [...set] : ['all']
  }

  // 供 generateBiData 使用的稳定快照（去掉 activePanel，切面板不改变数据 seed）
  const dataState = (): BiState => ({ time: { ...state.time }, warehouses: [...state.warehouses] })

  return {
    state: readonly(state),
    setPreset,
    setCustomRange,
    setPanel,
    toggleWarehouse,
    dataState,
  }
}
