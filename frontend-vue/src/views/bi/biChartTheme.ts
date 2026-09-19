/**
 * BI 图表 ECharts 基础样式：统一 Apple 观感（去网格、圆角柱、字号、配色）。
 */
import type { EChartsOption } from 'echarts'
import * as echarts from 'echarts'
import { BI_THEME } from '@/api/mock/bi'

export const BI_PALETTE = [
  BI_THEME.blue, BI_THEME.green, BI_THEME.orange, BI_THEME.purple,
  BI_THEME.cyan, BI_THEME.red, BI_THEME.blueLight, BI_THEME.indigo,
]

const FONT = "-apple-system, 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif"

/** 生成一份合并了基础样式的 option */
export function biOption(opt: EChartsOption): EChartsOption {
  return {
    color: BI_PALETTE,
    textStyle: { fontFamily: FONT, color: BI_THEME.grey },
    animationDuration: 600,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: 'rgba(0,0,0,0.06)',
      borderWidth: 1,
      textStyle: { color: '#1d1d1f', fontSize: 12, fontFamily: FONT },
      extraCssText: 'box-shadow:0 8px 28px rgba(0,0,0,0.12);border-radius:12px;',
      axisPointer: { type: 'shadow' },
      ...(opt.tooltip as object | undefined),
    },
    grid: { left: 8, right: 18, top: 34, bottom: 8, containLabel: true, ...(opt.grid as object | undefined) },
    ...opt,
  }
}

/** 触发浏览器下载一张 dataURL 图片 */
export function downloadDataUrl(dataUrl: string, filename: string) {
  if (!dataUrl) return
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  a.click()
}

/** 文件名时间戳 yyyyMMddHHmmss */
export function stamp(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}

/** 导出一个面板内所有 ECharts 图表为 PNG（逐图下载） */
export function exportPanelCharts(root: HTMLElement | null, panelName: string) {
  if (!root) return
  const nodes = Array.from(root.querySelectorAll<HTMLElement>('.bi-chart'))
  nodes.forEach((node, i) => {
    const inst = echarts.getInstanceByDom(node)
    if (!inst) return
    const url = inst.getDataURL({ pixelRatio: 2, backgroundColor: '#fff' })
    downloadDataUrl(url, `业财BI-${panelName}-${i + 1}-${stamp()}.png`)
  })
}

/** 通用类目/数值坐标轴样式 */
export const axisCategory = (data: string[], extra: Record<string, unknown> = {}) => ({
  type: 'category' as const,
  data,
  axisLine: { lineStyle: { color: BI_THEME.greyLight } },
  axisTick: { show: false },
  axisLabel: { color: BI_THEME.grey, fontSize: 11 },
  ...extra,
})
export const axisValue = (extra: Record<string, unknown> = {}) => ({
  type: 'value' as const,
  splitLine: { lineStyle: { color: 'rgba(0,0,0,0.05)' } },
  axisLabel: { color: BI_THEME.grey, fontSize: 11 },
  ...extra,
})
