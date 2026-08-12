<script setup lang="ts">
/**
 * 数据看板（首页）— 可视化大屏风格
 * 美化统计卡片 + ECharts 图表 + Mock 数据
 */
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import {
  Download,
  Upload,
  Box,
  Van,
  Goods,
  Warning,
  ShoppingCart,
  User,
  TrendCharts,
  PieChart,
  Histogram,
  Rank,
  Switch,
  EditPen,
  DataBoard,
  RefreshLeft,
} from '@element-plus/icons-vue'
import { getDashboardSummary, type DashboardSummary } from '@/api'

// ============ Mock 数据（接口失败或无数据时使用） ============
const mockSummary: DashboardSummary = {
  todayInboundCount: 128,
  todayOutboundCount: 96,
  pendingInboundCount: 23,
  pendingOutboundCount: 37,
  totalInventoryQty: 58420,
  lowStockProductCount: 12,
  activeProductCount: 326,
  activeCustomerCount: 84,
}

// 近7天出入库趋势
const mockTrendData = {
  dates: ['08-06', '08-07', '08-08', '08-09', '08-10', '08-11', '08-12'],
  inbound: [86, 102, 78, 135, 94, 110, 128],
  outbound: [62, 88, 71, 104, 82, 91, 96],
}

// 库存分类占比
const mockCategoryPie = [
  { name: '电子产品', value: 18600 },
  { name: '服装鞋帽', value: 14200 },
  { name: '家居日用', value: 10800 },
  { name: '美妆个护', value: 7500 },
  { name: '食品饮料', value: 4320 },
  { name: '其他', value: 3000 },
]

// 各仓库库存分布
const mockWarehouseBar = {
  warehouses: ['上海仓', '广州仓', '北京仓', '成都仓', '武汉仓'],
  available: [12400, 9800, 8600, 7200, 6300],
  locked: [2100, 1800, 1500, 1200, 980],
}

// 商品销量 Top10
const mockTopSales = [
  { name: 'iPhone 15 Pro Max 256G', value: 428 },
  { name: 'AirPods Pro 2代', value: 356 },
  { name: '戴森吹风机 HD15', value: 289 },
  { name: 'SK-II神仙水 230ml', value: 245 },
  { name: 'Nike Air Max 跑鞋', value: 212 },
  { name: '小米扫地机器人', value: 186 },
  { name: '雅诗兰黛小棕瓶', value: 168 },
  { name: 'Levi\'s 501牛仔裤', value: 152 },
  { name: 'Apple Watch S9', value: 138 },
  { name: '无印良品乳胶枕', value: 124 },
]

// 单据状态分布
const mockOrderStatusPie = [
  { name: '待处理', value: 60 },
  { name: '进行中', value: 82 },
  { name: '已完成', value: 245 },
  { name: '已取消', value: 18 },
]

// ============ 核心 KPI 指标卡 Mock 数据 ============
// 库存周转率 / 库容使用率 / 今日订单量 / 作业效率（计划 vs 完成）
const mockKpi = {
  turnoverRate: 4.2, // 次/月
  turnoverTrend: 8.5,
  capacityUsed: 78, // %
  capacityTotal: 75000, // 件
  capacityUsedQty: 58420, // 件
  todayOrderCount: 1284, // 单
  todayOrderTrend: 12.5,
  inboundPlan: 150,
  inboundDone: 138,
  outboundPlan: 120,
  outboundDone: 104,
}

// 仓库热力图：行=库区，列=货架列，值=繁忙程度 0-100
const mockHeatmap = {
  zones: ['A 区', 'B 区', 'C 区', 'D 区', 'E 区'],
  cols: ['1 列', '2 列', '3 列', '4 列', '5 列', '6 列', '7 列', '8 列'],
  // data: [colIndex, zoneIndex, value]
  data: [
    [0, 0, 88], [1, 0, 95], [2, 0, 72], [3, 0, 45], [4, 0, 30], [5, 0, 62], [6, 0, 80], [7, 0, 92],
    [0, 1, 60], [1, 1, 78], [2, 1, 90], [3, 1, 85], [4, 1, 55], [5, 1, 40], [6, 1, 68], [7, 1, 75],
    [0, 2, 35], [1, 2, 50], [2, 2, 65], [3, 2, 82], [4, 2, 95], [5, 2, 88], [6, 2, 70], [7, 2, 48],
    [0, 3, 92], [1, 3, 86], [2, 3, 70], [3, 3, 52], [4, 3, 38], [5, 3, 65], [6, 3, 78], [7, 3, 84],
    [0, 4, 42], [1, 4, 58], [2, 4, 72], [3, 4, 80], [4, 4, 68], [5, 4, 50], [6, 4, 36], [7, 4, 62],
  ],
}

// 库存预警列表（低库存 + 临期商品）
const mockStockAlerts = [
  { type: '低库存', productName: 'iPhone 15 Pro Max 256G', sku: 'IP15PM-256', warehouse: '上海仓', qty: 5, threshold: 20, level: 'danger' },
  { type: '低库存', productName: 'AirPods Pro 2代', sku: 'APP-2', warehouse: '广州仓', qty: 8, threshold: 30, level: 'danger' },
  { type: '临期', productName: 'SK-II神仙水 230ml', sku: 'SK2-230', warehouse: '北京仓', qty: 42, threshold: 0, expireDays: 15, level: 'warning' },
  { type: '低库存', productName: '戴森吹风机 HD15', sku: 'DY-HD15', warehouse: '成都仓', qty: 3, threshold: 15, level: 'danger' },
  { type: '临期', productName: '雅诗兰黛小棕瓶 50ml', sku: 'EL-EB50', warehouse: '上海仓', qty: 28, threshold: 0, expireDays: 7, level: 'warning' },
]

// 待办事项与消息列表
const mockTodos = [
  { title: '3 张入库单待审核', desc: '上海仓 · 供应商：华为科技', tag: '入库审核', type: 'warning', time: '10 分钟前' },
  { title: '5 张出库单待发货', desc: '广州仓 · 客户：京东自营', tag: '出库发货', type: 'danger', time: '32 分钟前' },
  { title: '2 个波次待拣货', desc: '波次号 WAVE-20260812-01', tag: '波次拣货', type: 'info', time: '1 小时前' },
  { title: '月末盘点任务待执行', desc: '全部仓库 · 计划 08-31 执行', tag: '盘点', type: 'primary', time: '2 小时前' },
  { title: '系统升级公告待确认', desc: 'v1.2.0 将于本周六凌晨停机维护', tag: '公告', type: 'success', time: '昨天' },
]

// ============ 数据层 ============
const summary = ref<DashboardSummary>(mockSummary)
const loading = ref(false)

const loadSummary = async () => {
  loading.value = true
  try {
    const res = await getDashboardSummary()
    summary.value = res.data || mockSummary
  } catch (e: any) {
    // 接口失败则使用 mock 数据
    summary.value = mockSummary
    console.warn('看板使用 Mock 数据:', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  await loadSummary()
  await nextTick()
  initCharts()
  window.addEventListener('resize', handleResize)
  // 等待布局稳定后校准一次图表尺寸，避免容器宽度未就绪导致的标签重叠
  setTimeout(handleResize, 300)
  // 监听图表容器尺寸变化（如 CSS 改动、侧边栏伸缩），自动同步 resize
  resizeObserver = new ResizeObserver(() => handleResize())
  ;[trendChartRef.value, categoryChartRef.value, warehouseChartRef.value, topSalesChartRef.value, orderStatusChartRef.value, heatmapChartRef.value].forEach((el) => {
    if (el) resizeObserver!.observe(el)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  disposeCharts()
})

// ============ 统计卡片配置（带渐变色 + 趋势） ============
interface CardConfig {
  key: keyof DashboardSummary
  label: string
  icon: any
  gradient: string
  shadow: string
  trend: number // 模拟环比百分比
  trendLabel: string
}

const cards: CardConfig[] = [
  {
    key: 'todayInboundCount',
    label: '今日入库单',
    icon: Download,
    gradient: 'linear-gradient(135deg, #2d4a8e 0%, #5470c6 100%)',
    shadow: '0 6px 20px rgba(84, 112, 198, 0.4)',
    trend: 12.5,
    trendLabel: '较昨日',
  },
  {
    key: 'todayOutboundCount',
    label: '今日出库单',
    icon: Upload,
    gradient: 'linear-gradient(135deg, #3a7a3f 0%, #6ba84f 100%)',
    shadow: '0 6px 20px rgba(107, 168, 79, 0.4)',
    trend: 8.3,
    trendLabel: '较昨日',
  },
  {
    key: 'pendingInboundCount',
    label: '待收货入库',
    icon: Box,
    gradient: 'linear-gradient(135deg, #8a5a0e 0%, #c98a1e 100%)',
    shadow: '0 6px 20px rgba(201, 138, 30, 0.4)',
    trend: -3.2,
    trendLabel: '较昨日',
  },
  {
    key: 'pendingOutboundCount',
    label: '待发货出库',
    icon: Van,
    gradient: 'linear-gradient(135deg, #1a5cb0 0%, #3a8de0 100%)',
    shadow: '0 6px 20px rgba(58, 141, 224, 0.4)',
    trend: 15.7,
    trendLabel: '较昨日',
  },
  {
    key: 'totalInventoryQty',
    label: '库存总量(件)',
    icon: Goods,
    gradient: 'linear-gradient(135deg, #1a6a8a 0%, #3a9ec0 100%)',
    shadow: '0 6px 20px rgba(58, 158, 192, 0.4)',
    trend: 2.1,
    trendLabel: '较上周',
  },
  {
    key: 'lowStockProductCount',
    label: '低库存商品',
    icon: Warning,
    gradient: 'linear-gradient(135deg, #a82828 0%, #d44848 100%)',
    shadow: '0 6px 20px rgba(212, 72, 72, 0.4)',
    trend: -5.4,
    trendLabel: '较昨日',
  },
  {
    key: 'activeProductCount',
    label: '在售商品数',
    icon: ShoppingCart,
    gradient: 'linear-gradient(135deg, #5a3088 0%, #7a4aa8 100%)',
    shadow: '0 6px 20px rgba(122, 74, 168, 0.4)',
    trend: 4.8,
    trendLabel: '较上月',
  },
  {
    key: 'activeCustomerCount',
    label: '合作客户数',
    icon: User,
    gradient: 'linear-gradient(135deg, #a04525 0%, #c96535 100%)',
    shadow: '0 6px 20px rgba(201, 101, 53, 0.4)',
    trend: 6.2,
    trendLabel: '较上月',
  },
]

const formatNumber = (n: number) => n.toLocaleString('zh-CN')

// ============ 快捷操作入口 ============
const router = useRouter()
const quickActions = [
  { label: '新建入库单', icon: Download, path: '/inbound', color: '#5470c6' },
  { label: '新建出库单', icon: Upload, path: '/outbound', color: '#91cc75' },
  { label: '波次拣货', icon: Box, path: '/waves', color: '#fac858' },
  { label: '库内移库', icon: Switch, path: '/transfers', color: '#73c0de' },
  { label: '库存调整', icon: EditPen, path: '/adjustments', color: '#ee6666' },
  { label: '快速盘点', icon: DataBoard, path: '/inventory', color: '#9a60b4' },
  { label: '批次管理', icon: Van, path: '/batches', color: '#fc8452' },
  { label: '退货管理', icon: RefreshLeft, path: '/returns', color: '#ea7ccc' },
]
const goAction = (path: string) => {
  router.push(path)
}

// 作业效率：入库 / 出库 完成率
const inboundEfficiency = computed(() =>
  mockKpi.inboundPlan === 0 ? 0 : Math.round((mockKpi.inboundDone / mockKpi.inboundPlan) * 100),
)
const outboundEfficiency = computed(() =>
  mockKpi.outboundPlan === 0 ? 0 : Math.round((mockKpi.outboundDone / mockKpi.outboundPlan) * 100),
)

// ============ ECharts 图表 ============
const trendChartRef = ref<HTMLDivElement | null>(null)
const categoryChartRef = ref<HTMLDivElement | null>(null)
const warehouseChartRef = ref<HTMLDivElement | null>(null)
const topSalesChartRef = ref<HTMLDivElement | null>(null)
const orderStatusChartRef = ref<HTMLDivElement | null>(null)
const heatmapChartRef = ref<HTMLDivElement | null>(null)

let trendChart: echarts.ECharts | null = null
let categoryChart: echarts.ECharts | null = null
let warehouseChart: echarts.ECharts | null = null
let topSalesChart: echarts.ECharts | null = null
let orderStatusChart: echarts.ECharts | null = null
let heatmapChart: echarts.ECharts | null = null

const palette = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']

const initTrendChart = () => {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: { color: '#333' },
    },
    legend: {
      data: ['入库单', '出库单'],
      top: 0,
      right: 20,
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { color: '#6b7280' },
    },
    grid: { left: 40, right: 20, top: 40, bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: mockTrendData.dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280' },
    },
    series: [
      {
        name: '入库单',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: mockTrendData.inbound,
        lineStyle: { width: 3, color: '#5470c6' },
        itemStyle: { color: '#5470c6', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(84, 112, 198, 0.35)' },
            { offset: 1, color: 'rgba(84, 112, 198, 0.02)' },
          ]),
        },
        label: {
          show: true,
          position: 'top',
          color: '#5470c6',
          fontSize: 11,
          fontWeight: 600,
        },
      },
      {
        name: '出库单',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: mockTrendData.outbound,
        lineStyle: { width: 3, color: '#91cc75' },
        itemStyle: { color: '#91cc75', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(145, 204, 117, 0.35)' },
            { offset: 1, color: 'rgba(145, 204, 117, 0.02)' },
          ]),
        },
        label: {
          show: true,
          position: 'bottom',
          color: '#91cc75',
          fontSize: 11,
          fontWeight: 600,
        },
      },
    ],
  }
  trendChart.setOption(option)
}

const initCategoryChart = () => {
  if (!categoryChartRef.value) return
  categoryChart = echarts.init(categoryChartRef.value)
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 件 ({d}%)',
      backgroundColor: 'rgba(255,255,255,0.95)',
      textStyle: { color: '#333' },
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      itemGap: 12,
      textStyle: { color: '#6b7280' },
    },
    color: palette,
    series: [
      {
        name: '库存分类',
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 3,
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 600 },
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
        },
        labelLine: { show: false },
        data: mockCategoryPie,
      },
    ],
  }
  categoryChart.setOption(option)
}

const initWarehouseChart = () => {
  if (!warehouseChartRef.value) return
  warehouseChart = echarts.init(warehouseChartRef.value)
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.95)',
      textStyle: { color: '#333' },
    },
    legend: {
      data: ['可用库存', '锁定库存'],
      top: 0,
      right: 10,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: { left: 10, right: 16, top: 45, bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: mockWarehouseBar.warehouses,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280' },
    },
    series: [
      {
        name: '可用库存',
        type: 'bar',
        stack: 'total',
        barWidth: '36%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#4facfe' },
            { offset: 1, color: '#00f2fe' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(79,172,254,0.5)' } },
        data: mockWarehouseBar.available,
      },
      {
        name: '锁定库存',
        type: 'bar',
        stack: 'total',
        barWidth: '36%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#fa709a' },
            { offset: 1, color: '#fee140' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(250,112,154,0.5)' } },
        data: mockWarehouseBar.locked,
      },
    ],
  }
  warehouseChart.setOption(option)
}

const initTopSalesChart = () => {
  if (!topSalesChartRef.value) return
  topSalesChart = echarts.init(topSalesChartRef.value)
  const sorted = [...mockTopSales].reverse()
  const names = sorted.map((i) => i.name)
  const values = sorted.map((i) => i.value)
  const maxVal = Math.max(...values)
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: '{b}: {c} 件',
      backgroundColor: 'rgba(255,255,255,0.95)',
      textStyle: { color: '#333' },
    },
    grid: { left: 10, right: 30, top: 20, bottom: 30, containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#374151',
        fontSize: 12,
        // 长名称截断，悬停 tooltip 仍显示全名
        formatter: (v: string) => (v.length > 10 ? v.slice(0, 10) + '…' : v),
      },
    },
    series: [
      {
        type: 'bar',
        barWidth: '56%',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            borderRadius: [0, 6, 6, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: palette[i % palette.length] + '33' },
              { offset: 1, color: palette[i % palette.length] },
            ]),
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: '#374151',
          fontWeight: 600,
          formatter: '{c}',
        },
      },
    ],
  }
  topSalesChart.setOption(option)
}

const initOrderStatusChart = () => {
  if (!orderStatusChartRef.value) return
  orderStatusChart = echarts.init(orderStatusChartRef.value)
  const total = mockOrderStatusPie.reduce((s, d) => s + d.value, 0)
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 单 ({d}%)',
      backgroundColor: 'rgba(255,255,255,0.95)',
      textStyle: { color: '#333' },
    },
    title: {
      text: `${total}`,
      subtext: '单据总数',
      left: '35%',
      top: 'center',
      textAlign: 'center',
      textVerticalAlign: 'middle',
      textStyle: { fontSize: 36, fontWeight: 700, color: '#1f2937' },
      subtextStyle: { fontSize: 13, color: '#9ca3af' },
    },
    legend: {
      orient: 'vertical',
      right: '10%',
      top: 'center',
      itemGap: 22,
      itemWidth: 12,
      itemHeight: 12,
      icon: 'circle',
      textStyle: { color: '#6b7280', fontSize: 14 },
      formatter: (name: string) => {
        const item = mockOrderStatusPie.find((d) => d.name === name)
        const pct = item ? ((item.value / total) * 100).toFixed(1) : '0.0'
        return `${name}    ${item?.value ?? 0} 单    ${pct}%`
      },
    },
    color: ['#E6A23C', '#409EFF', '#67C23A', '#909399'],
    series: [
      {
        name: '单据状态',
        type: 'pie',
        radius: ['58%', '78%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 3,
        },
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scaleSize: 6,
          itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.15)' },
        },
        data: mockOrderStatusPie,
      },
    ],
  }
  orderStatusChart.setOption(option)
}

const initHeatmapChart = () => {
  if (!heatmapChartRef.value) return
  heatmapChart = echarts.init(heatmapChartRef.value)
  const zoneLabels = mockHeatmap.zones
  const colLabels = mockHeatmap.cols
  const option: echarts.EChartsOption = {
    tooltip: {
      position: 'top',
      formatter: (p: any) =>
        `${zoneLabels[p.value[1]]} · ${colLabels[p.value[0]]}<br/>繁忙程度：<b>${p.value[2]}</b>`,
      backgroundColor: 'rgba(255,255,255,0.95)',
      textStyle: { color: '#333' },
    },
    grid: { left: 50, right: 20, top: 30, bottom: 60, containLabel: true },
    xAxis: {
      type: 'category',
      data: colLabels,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'category',
      data: zoneLabels,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#6b7280' },
      inRange: {
        color: ['#e0f2fe', '#7dd3fc', '#38bdf8', '#0284c7', '#075985'],
      },
    },
    series: [
      {
        name: '繁忙程度',
        type: 'heatmap',
        data: mockHeatmap.data,
        label: { show: true, color: '#1f2937', fontSize: 11, fontWeight: 600 },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
        },
      },
    ],
  }
  heatmapChart.setOption(option)
}

const initCharts = () => {
  initTrendChart()
  initCategoryChart()
  initWarehouseChart()
  initTopSalesChart()
  initOrderStatusChart()
  initHeatmapChart()
}

const disposeCharts = () => {
  trendChart?.dispose()
  categoryChart?.dispose()
  warehouseChart?.dispose()
  topSalesChart?.dispose()
  orderStatusChart?.dispose()
  heatmapChart?.dispose()
}

const handleResize = () => {
  trendChart?.resize()
  categoryChart?.resize()
  warehouseChart?.resize()
  topSalesChart?.resize()
  orderStatusChart?.resize()
  heatmapChart?.resize()
}
</script>

<template>
  <div class="dashboard-wrap">
    <!-- ========== 核心 KPI 指标卡 ========== -->
    <div class="kpi-grid">
      <!-- 库存周转率 -->
      <div class="kpi-card kpi-turnover">
        <div class="kpi-head">
          <span class="kpi-label">库存周转率</span>
          <el-icon :size="18" color="#5470c6"><TrendCharts /></el-icon>
        </div>
        <div class="kpi-value">
          {{ mockKpi.turnoverRate }} <span class="kpi-unit">次/月</span>
        </div>
        <div class="kpi-trend up">
          <el-icon :size="12"><Top /></el-icon>
          <span>{{ mockKpi.turnoverTrend }}%</span>
          <span class="kpi-trend-label">较上月</span>
        </div>
      </div>

      <!-- 库容使用率 -->
      <div class="kpi-card kpi-capacity">
        <div class="kpi-head">
          <span class="kpi-label">库容使用率</span>
          <el-icon :size="18" color="#3a9ec0"><DataBoard /></el-icon>
        </div>
        <div class="kpi-value">
          {{ mockKpi.capacityUsed }}<span class="kpi-unit">%</span>
        </div>
        <el-progress
          :percentage="mockKpi.capacityUsed"
          :stroke-width="8"
          :show-text="false"
          color="#3a9ec0"
          class="kpi-progress"
        />
        <div class="kpi-sub">
          {{ formatNumber(mockKpi.capacityUsedQty) }} / {{ formatNumber(mockKpi.capacityTotal) }} 件
        </div>
      </div>

      <!-- 今日订单量 -->
      <div class="kpi-card kpi-order">
        <div class="kpi-head">
          <span class="kpi-label">今日订单量</span>
          <el-icon :size="18" color="#6ba84f"><ShoppingCart /></el-icon>
        </div>
        <div class="kpi-value">
          {{ formatNumber(mockKpi.todayOrderCount) }} <span class="kpi-unit">单</span>
        </div>
        <div class="kpi-trend up">
          <el-icon :size="12"><Top /></el-icon>
          <span>{{ mockKpi.todayOrderTrend }}%</span>
          <span class="kpi-trend-label">较昨日</span>
        </div>
      </div>

      <!-- 作业效率 -->
      <div class="kpi-card kpi-efficiency">
        <div class="kpi-head">
          <span class="kpi-label">作业效率</span>
          <el-icon :size="18" color="#c98a1e"><Histogram /></el-icon>
        </div>
        <div class="efficiency-row">
          <div class="efficiency-item">
            <span class="eff-label">入库</span>
            <el-progress
              :percentage="inboundEfficiency"
              :stroke-width="8"
              :show-text="false"
              color="#5470c6"
              class="eff-progress"
            />
            <span class="eff-num">{{ mockKpi.inboundDone }}/{{ mockKpi.inboundPlan }}</span>
          </div>
          <div class="efficiency-item">
            <span class="eff-label">出库</span>
            <el-progress
              :percentage="outboundEfficiency"
              :stroke-width="8"
              :show-text="false"
              color="#91cc75"
              class="eff-progress"
            />
            <span class="eff-num">{{ mockKpi.outboundDone }}/{{ mockKpi.outboundPlan }}</span>
          </div>
        </div>
        <div class="kpi-sub">完成量 / 计划量</div>
      </div>
    </div>

    <!-- ========== 统计卡片区域 ========== -->
    <div class="stat-grid">
      <div
        v-for="(c, idx) in cards"
        :key="c.key"
        class="stat-card"
        :style="{ background: c.gradient, boxShadow: c.shadow, animationDelay: idx * 60 + 'ms' }"
      >
        <div class="stat-icon-wrap">
          <el-icon :size="20" color="#fff"><component :is="c.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">
            {{ summary ? formatNumber((summary as any)[c.key] ?? 0) : '-' }}
          </div>
          <div class="stat-trend" :class="c.trend >= 0 ? 'up' : 'down'">
            <el-icon :size="12">
              <component :is="c.trend >= 0 ? 'Top' : 'Bottom'" />
            </el-icon>
            <span>{{ Math.abs(c.trend) }}%</span>
            <span class="trend-label">{{ c.trendLabel }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 图表区域第一行：近7天出入库趋势 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#5470c6"><TrendCharts /></el-icon>
              <span>近7天出入库趋势</span>
            </div>
            <div class="panel-sub">INBOUND / OUTBOUND · 7 DAYS</div>
          </div>
          <div ref="trendChartRef" class="chart-box chart-lg"></div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 图表区域第二行：单据状态分布 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#91cc75"><PieChart /></el-icon>
              <span>单据状态分布</span>
            </div>
            <div class="panel-sub">ORDER STATUS</div>
          </div>
          <div ref="orderStatusChartRef" class="chart-box chart-lg"></div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 图表区域第三行：分类环形图 + 仓库库存 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="10">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#fac858"><PieChart /></el-icon>
              <span>库存分类占比</span>
            </div>
            <div class="panel-sub">CATEGORY SHARE</div>
          </div>
          <div ref="categoryChartRef" class="chart-box chart-md"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="14">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#73c0de"><Histogram /></el-icon>
              <span>各仓库库存分布</span>
            </div>
            <div class="panel-sub">WAREHOUSE INVENTORY</div>
          </div>
          <div ref="warehouseChartRef" class="chart-box chart-md"></div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 图表区域第三行：商品销量排行 + 系统公告 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="15">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#ee6666"><Rank /></el-icon>
              <span>商品销量 TOP 10</span>
            </div>
            <div class="panel-sub">TOP SALES · MOCK</div>
          </div>
          <div ref="topSalesChartRef" class="chart-box chart-xl"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="9">
        <div class="panel notice-panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#9a60b4"><Box /></el-icon>
              <span>系统公告</span>
            </div>
            <div class="panel-sub">ANNOUNCEMENT</div>
          </div>
          <div class="notice-list">
            <div class="notice-item">
              <span class="notice-dot dot-blue"></span>
              <div class="notice-body">
                <div class="notice-title">WMS MVP 已上线</div>
                <div class="notice-desc">支持客户分层管理、入库/出库/移库/调整全流程、批次与流水追溯。</div>
                <div class="notice-time">2026-08-10</div>
              </div>
            </div>
            <div class="notice-item">
              <span class="notice-dot dot-green"></span>
              <div class="notice-body">
                <div class="notice-title">库存预警规则已优化</div>
                <div class="notice-desc">库存总量统计「可用 + 锁定」，低库存商品阈值 10 件，支持自定义阈值。</div>
                <div class="notice-time">2026-08-08</div>
              </div>
            </div>
            <div class="notice-item">
              <span class="notice-dot dot-orange"></span>
              <div class="notice-body">
                <div class="notice-title">波次拣货公测中</div>
                <div class="notice-desc">智能合并订单生成拣货波次，大幅提升出库效率，欢迎试用反馈。</div>
                <div class="notice-time">2026-08-05</div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 仓库热力图 + 预警与待办中心 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="13">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#0284c7"><DataBoard /></el-icon>
              <span>仓库热力图</span>
            </div>
            <div class="panel-sub">WAREHOUSE HEATMAP</div>
          </div>
          <div ref="heatmapChartRef" class="chart-box chart-md"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="11">
        <div class="panel alert-panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#ee6666"><Warning /></el-icon>
              <span>库存预警</span>
            </div>
            <div class="panel-sub">STOCK ALERTS</div>
          </div>
          <div class="alert-list">
            <div v-for="(a, i) in mockStockAlerts" :key="i" class="alert-item">
              <el-tag :type="a.level as any" size="small" effect="dark" class="alert-tag">{{ a.type }}</el-tag>
              <div class="alert-body">
                <div class="alert-title">
                  {{ a.productName }}
                  <span class="alert-sku">{{ a.sku }}</span>
                </div>
                <div class="alert-desc">
                  <span>{{ a.warehouse }}</span>
                  <template v-if="a.type === '低库存'">
                    · 当前 <b class="alert-danger">{{ a.qty }}</b> / 阈值 {{ a.threshold }}
                  </template>
                  <template v-else>
                    · 剩余 <b class="alert-warning">{{ a.expireDays }}</b> 天到期
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 待办事项与消息 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#5470c6"><List /></el-icon>
              <span>待办事项与消息</span>
            </div>
            <div class="panel-sub">TODO &amp; MESSAGES</div>
          </div>
          <div class="todo-grid">
            <div v-for="(t, i) in mockTodos" :key="i" class="todo-card">
              <el-tag :type="t.type as any" size="small" effect="plain" class="todo-tag">{{ t.tag }}</el-tag>
              <div class="todo-title">{{ t.title }}</div>
              <div class="todo-desc">{{ t.desc }}</div>
              <div class="todo-time">{{ t.time }}</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ========== 快捷操作与入口 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <el-icon color="#91cc75"><Grid /></el-icon>
              <span>快捷操作</span>
            </div>
            <div class="panel-sub">QUICK ACTIONS</div>
          </div>
          <div class="quick-grid">
            <div
              v-for="a in quickActions"
              :key="a.path"
              class="quick-item"
              @click="goAction(a.path)"
            >
              <div class="quick-icon" :style="{ background: a.color + '1a', color: a.color }">
                <el-icon :size="22"><component :is="a.icon" /></el-icon>
              </div>
              <span class="quick-label">{{ a.label }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard-wrap {
  padding: 4px 0 24px;
}

/* ============ 核心 KPI 指标卡 ============ */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}
.kpi-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid #f1f5f9;
  position: relative;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.kpi-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}
.kpi-turnover::before { background: #5470c6; }
.kpi-capacity::before { background: #3a9ec0; }
.kpi-order::before { background: #6ba84f; }
.kpi-efficiency::before { background: #c98a1e; }
.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.09);
}
.kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.kpi-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}
.kpi-value {
  font-size: 30px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
  font-family: 'DIN', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.kpi-unit {
  font-size: 13px;
  font-weight: 500;
  color: #9ca3af;
  margin-left: 4px;
}
.kpi-trend {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  margin-top: 8px;
  padding: 2px 8px;
  border-radius: 10px;
}
.kpi-trend.up {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}
.kpi-trend.down {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}
.kpi-trend-label {
  color: #9ca3af;
  margin-left: 2px;
}
.kpi-progress {
  margin-top: 10px;
}
.kpi-sub {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 6px;
}
.efficiency-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}
.efficiency-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.eff-label {
  font-size: 12px;
  color: #6b7280;
  width: 32px;
  flex-shrink: 0;
}
.eff-progress {
  flex: 1;
}
.eff-num {
  font-size: 12px;
  color: #374151;
  font-weight: 600;
  width: 56px;
  text-align: right;
  flex-shrink: 0;
}

/* ============ 库存预警 ============ */
.alert-panel .chart-box {
  flex: none;
}
.alert-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}
.alert-item:last-child {
  border-bottom: none;
}
.alert-tag {
  flex-shrink: 0;
  margin-top: 2px;
}
.alert-body {
  flex: 1;
  min-width: 0;
}
.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}
.alert-sku {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 400;
  margin-left: 6px;
}
.alert-desc {
  font-size: 12px;
  color: #6b7280;
}
.alert-danger {
  color: #f56c6c;
}
.alert-warning {
  color: #e6a23c;
}

/* ============ 待办事项与消息 ============ */
.todo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.todo-card {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 14px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.todo-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
}
.todo-tag {
  margin-bottom: 8px;
}
.todo-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}
.todo-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  margin-bottom: 6px;
}
.todo-time {
  font-size: 11px;
  color: #9ca3af;
}

/* ============ 快捷操作 ============ */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 16px;
}
.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}
.quick-item:hover {
  background: #f5f7fa;
  transform: translateY(-2px);
}
.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quick-label {
  font-size: 12px;
  color: #374151;
  text-align: center;
  white-space: nowrap;
}

/* ============ 统计卡片 ============ */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}
.stat-card {
  position: relative;
  border-radius: 12px;
  padding: 10px 16px;
  height: 70px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
  opacity: 0;
  transform: translateY(12px);
  animation: fadeUp 0.5s ease forwards;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
}
/* 装饰圆：固定在右下角，不遮挡内容 */
.stat-card::after {
  content: '';
  position: absolute;
  right: -20px;
  bottom: -20px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  pointer-events: none;
  z-index: 0;
}
.stat-icon-wrap {
  position: relative;
  z-index: 1;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-info {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
}
.stat-label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 2px;
  letter-spacing: 0.3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 2px;
  font-family: 'DIN', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  white-space: nowrap;
}
.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(2px);
}
.stat-trend.up {
  color: #d4f7dc;
}
.stat-trend.down {
  color: #ffd7d7;
}
.trend-label {
  opacity: 0.85;
  margin-left: 2px;
}

@keyframes fadeUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============ 面板容器 ============ */
.chart-row {
  margin-bottom: 24px;
  /* 窄屏下列换行堆叠时，行与行之间也保持缝隙 */
  row-gap: 24px;
}
.chart-row:last-child {
  margin-bottom: 0;
}
.panel {
  background: #fff;
  border-radius: 14px;
  padding: 18px 22px 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid #f1f5f9;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.panel:hover {
  /* 上浮 + 收敛阴影，避免悬停阴影盖住相邻面板 */
  transform: translateY(-3px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.09);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #eef2f7;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}
.panel-sub {
  font-size: 11px;
  color: #9ca3af;
  letter-spacing: 0.8px;
  font-weight: 500;
}

/* ============ 图表容器 ============ */
.chart-box {
  width: 100%;
  flex: none;
}
.chart-lg {
  height: 500px;
}
.chart-md {
  height: 500px;
}
.chart-xl {
  height: 360px;
}

/* ============ 系统公告 ============ */
.notice-panel .chart-box {
  flex: none;
}
.notice-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.notice-item {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #f3f4f6;
}
.notice-item:last-child {
  border-bottom: none;
}
.notice-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.03);
}
.dot-blue {
  background: #409eff;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.15);
}
.dot-green {
  background: #67c23a;
  box-shadow: 0 0 0 4px rgba(103, 194, 58, 0.15);
}
.dot-orange {
  background: #e6a23c;
  box-shadow: 0 0 0 4px rgba(230, 162, 60, 0.15);
}
.notice-body {
  flex: 1;
  min-width: 0;
}
.notice-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}
.notice-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.55;
  margin-bottom: 6px;
}
.notice-time {
  font-size: 12px;
  color: #9ca3af;
}

/* ============ 响应式微调 ============ */
@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .quick-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .stat-card {
    height: 60px;
    padding: 8px 14px;
    gap: 10px;
  }
  .stat-icon-wrap {
    width: 32px;
    height: 32px;
    border-radius: 8px;
  }
  .stat-value {
    font-size: 18px;
  }
  .kpi-value {
    font-size: 24px;
  }
  .chart-lg,
  .chart-md,
  .chart-xl {
    height: 260px;
  }
  .panel {
    padding: 14px 16px 10px;
  }
}
</style>
