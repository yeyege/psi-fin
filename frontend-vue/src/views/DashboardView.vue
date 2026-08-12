<script setup lang="ts">
/**
 * 数据看板（首页）— 可视化大屏风格
 * 美化统计卡片 + ECharts 图表 + Mock 数据
 */
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
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
  ;[trendChartRef.value, categoryChartRef.value, warehouseChartRef.value, topSalesChartRef.value, orderStatusChartRef.value].forEach((el) => {
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

// ============ ECharts 图表 ============
const trendChartRef = ref<HTMLDivElement | null>(null)
const categoryChartRef = ref<HTMLDivElement | null>(null)
const warehouseChartRef = ref<HTMLDivElement | null>(null)
const topSalesChartRef = ref<HTMLDivElement | null>(null)
const orderStatusChartRef = ref<HTMLDivElement | null>(null)

let trendChart: echarts.ECharts | null = null
let categoryChart: echarts.ECharts | null = null
let warehouseChart: echarts.ECharts | null = null
let topSalesChart: echarts.ECharts | null = null
let orderStatusChart: echarts.ECharts | null = null

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

const initCharts = () => {
  initTrendChart()
  initCategoryChart()
  initWarehouseChart()
  initTopSalesChart()
  initOrderStatusChart()
}

const disposeCharts = () => {
  trendChart?.dispose()
  categoryChart?.dispose()
  warehouseChart?.dispose()
  topSalesChart?.dispose()
  orderStatusChart?.dispose()
}

const handleResize = () => {
  trendChart?.resize()
  categoryChart?.resize()
  warehouseChart?.resize()
  topSalesChart?.resize()
  orderStatusChart?.resize()
}
</script>

<template>
  <div class="dashboard-wrap">
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
  </div>
</template>

<style scoped>
.dashboard-wrap {
  padding: 4px 0 24px;
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
}
@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: 1fr;
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
