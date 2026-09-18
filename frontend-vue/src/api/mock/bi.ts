/**
 * BI 工作台 Mock 数据层
 *
 * 移植自原型 apple-store-wms.html 的 seeded PRNG + 四大视图生成器。
 * 关键点：
 *  - 纯函数、零网络请求，面板直接 import（不注册进 axios mockAdapter）
 *  - seed 由筛选状态派生 → 相同条件数据稳定不横跳，换条件产生合理差异
 *  - 返回结构沿用原型 camelCase 命名，便于后续替换为真实 /api/bi/* 聚合
 */

/* ============ 设计常量（与原型一致） ============ */
export const BI_THEME = {
  blue: '#0071e3', blueLight: '#2997ff',
  green: '#34c759', greenLight: '#5ad77a',
  orange: '#ff9500', orangeLight: '#ffb340',
  red: '#ff3b30', redLight: '#ff6b6b',
  purple: '#af52de', purpleLight: '#c77dff',
  indigo: '#5856d6', cyan: '#3a9ec0',
  grey: '#86868b', greyLight: '#d2d2d7',
} as const

export const WH_LIST = [
  { id: 'sh', name: '上海仓' },
  { id: 'gz', name: '广州仓' },
  { id: 'bj', name: '北京仓' },
  { id: 'cd', name: '成都仓' },
  { id: 'wh', name: '武汉仓' },
] as const

const SKU_POOL: [string, string][] = [
  ['iPhone 15 Pro Max 256G', 'IP15PM-256'],
  ['iPhone 15 Pro 128G', 'IP15P-128'],
  ['AirPods Pro 2代', 'APP-2'],
  ['MacBook Pro 14 M3', 'MBP14-M3'],
  ['iPad Air 5 256G', 'IPAD-A5'],
  ['Apple Watch S9', 'AWS-9'],
  ['戴森吹风机 HD15', 'DY-HD15'],
  ['戴森吸尘器 V15', 'DY-V15'],
  ['SK-II神仙水 230ml', 'SK2-230'],
  ['雅诗兰黛小棕瓶 50ml', 'EL-EB50'],
  ['兰蔻粉水 400ml', 'LC-400'],
  ['海蓝之谜面霜 60ml', 'LAM-60'],
  ['华为Mate60 Pro 256G', 'HW-M60P'],
  ['小米14 Ultra 256G', 'MI-14U'],
  ['索尼WH-1000XM5', 'SN-WH1K5'],
  ['Bose QC Ultra', 'BOSE-QCU'],
  ['任天堂Switch OLED', 'NS-OLED'],
  ['PS5 光驱版', 'PS5-DRV'],
  ['大疆Mini 4 Pro', 'DJ-M4P'],
  ['GoPro Hero 12', 'GP-H12'],
  ['茅台飞天53度500ml', 'MT-FT53'],
  ['五粮液普五52度', 'WLY-P5'],
  ['雀巢胶囊咖啡机', 'NES-C100'],
  ['飞利浦电动牙刷9系', 'HPP-9000'],
  ['博朗9系剃须刀', 'BR-9'],
  ['乐高哈利波特城堡', 'LEGO-HP'],
  ['Kindle Oasis', 'KD-Oasis'],
  ['小米扫地机器人S8', 'MI-S8'],
  ['石头扫地机器人G20', 'ROB-G20'],
  ['美的破壁机', 'MD-PB'],
]
const WORKERS = ['张伟', '李娜', '王芳', '刘洋', '陈静', '杨勇', '赵敏', '黄磊', '周强', '吴刚', '徐敏', '孙莉']
const VENDORS = ['华为科技', '小米供应链', '苹果中国', '宝洁中国', '联合利华', '欧莱雅集团', '戴森中国', '苏宁物流', '京东商采', '天猫超市', '大疆创新', '索尼中国']
const CUSTOMERS = ['京东自营', '天猫旗舰店', '拼多多百亿', '唯品会', '苏宁易购', '考拉海购', '得物APP', '小红书自营', '国美在线', '一号店', '沃尔玛中国', '大润发']
const RETURN_REASONS = [
  { name: '质量问题', color: BI_THEME.red },
  { name: '错发/漏发', color: BI_THEME.orange },
  { name: '物流破损', color: BI_THEME.blue },
  { name: '客户无理由', color: BI_THEME.grey },
]

/* ============ 状态类型 ============ */
export type BiPreset = 'today' | '7d' | '30d' | 'custom'
export interface BiTimeRange { preset: BiPreset; start: string | null; end: string | null }
export interface BiState { time: BiTimeRange; warehouses: string[] }
export type BiView = 'overview' | 'inventory' | 'flow' | 'efficiency'

/* ============ 工具函数（seeded） ============ */
export function hashString(s: string): number {
  let h = 2166136261 >>> 0
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return h >>> 0
}
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return function () {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const randRange = (rng: () => number, min: number, max: number) => min + rng() * (max - min)
const randInt = (rng: () => number, min: number, max: number) => Math.floor(randRange(rng, min, max + 1))
const pickItem = <T>(rng: () => number, arr: readonly T[]): T => arr[Math.floor(rng() * arr.length)]
const fmt = (n: number, d = 0) => (Number(n) || 0).toLocaleString('zh-CN', { maximumFractionDigits: d, minimumFractionDigits: d })
function dateArr(days: number): string[] {
  const out: string[] = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i)
    out.push(String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'))
  }
  return out
}
/** seed 由筛选状态派生：view + preset + 起止 + 排序后仓库集合 */
function getSeed(view: BiView, state: BiState): number {
  const whs = [...state.warehouses].sort().join(',')
  return hashString(`${view}|${state.time.preset}|${state.time.start ?? ''}|${state.time.end ?? ''}|${whs}`)
}
function dateRangeOf(state: BiState): number {
  switch (state.time.preset) {
    case 'today': return 1
    case '30d': return 30
    case 'custom': {
      if (state.time.start && state.time.end) {
        const s = new Date(state.time.start), e = new Date(state.time.end)
        return Math.max(1, Math.ceil((e.getTime() - s.getTime()) / 86400000) + 1)
      }
      return 7
    }
    default: return 7
  }
}
function activeWarehouses(state: BiState) {
  if (state.warehouses.includes('all')) return WH_LIST.slice()
  return WH_LIST.filter((w) => state.warehouses.includes(w.id))
}

/* ============ 返回结构类型 ============ */
export interface OverviewKpi { label: string; value?: string | number; unit?: string; trend?: 'up' | 'down'; trendVal?: string; progress?: number; sub?: string; rows?: { name: string; done: number; plan: number }[]; icon: string }
export interface OverviewStat { label: string; value: string | number; gradient: [string, string]; type?: string }
export interface OverviewAlert { level: 'danger' | 'warning'; tag: string; title: string; sku: string; warehouse: string; current: number; threshold: number; daysLeft: number; price: number }
export interface OverviewTodo { tagText: string; title: string; desc: string; time: string; color: string }
export interface OverviewData {
  kpis: OverviewKpi[]
  stats: OverviewStat[]
  trend: { labels: string[]; inbound: number[]; outbound: number[] }
  orderStatus: { name: string; value: number; color: string }[]
  whInventory: { name: string; available: number; locked: number }[]
  alerts: OverviewAlert[]
  todos: OverviewTodo[]
}
export interface InventoryData {
  skuTop10: { sku: string; name: string; qty: number; pct: number }[]
  lowStockList: { name: string; qty: number }[]
  ageDistribution: { range: string; color: string; skuCount: number; amount: number }[]
  batchStatus: { name: string; normal: number; nearExpire: number; expired: number; frozen: number }[]
  abc: { sku: string; amount: number; cumulativePct: number; category: 'A' | 'B' | 'C' }[]
}
export interface FlowData {
  trend30: { labels: string[]; inQty: number[]; outQty: number[]; inAmt: number[]; outAmt: number[] }
  netIn: number; netOut: number; netVal: number
  vendors: { vendor: string; amount: number; orderCount: number; onTimeRate: number }[]
  customers: { customer: string; amount: number; orderCount: number; returnRate: number }[]
  returnTrend: { labels: string[]; values: number[] }
  avgRetRate: number
  returnReasons: { name: string; color: string; count: number }[]
}
export interface EfficiencyTask { no: string; type: string; worker: string; startTime: string; progress: number; status: string }
export interface EfficiencyData {
  workerDaily: { worker: string; days: number[]; avg: number }[]
  dayLabels: string[]
  avgEff: number
  waveStatus: { name: string; value: number; color: string }[]
  wavePct: number; waveTotal: number
  durationTypes: { type: string; p10: number; p25: number; p50: number; p75: number; p90: number; color: string }[]
  tasks: EfficiencyTask[]
  taskTotal: number
}

/* ============ Overview ============ */
function mockOverview(state: BiState): OverviewData {
  const rng = mulberry32(getSeed('overview', state))
  const days = dateRangeOf(state)
  const whs = activeWarehouses(state)
  const whFactor = whs.length / WH_LIST.length
  const labels = dateArr(days)

  const turnoverRate = randRange(rng, 3.2, 5.4)
  const capacityPct = Math.round(randRange(rng, 55, 92))
  const totalCap = 75000
  const totalStock = Math.round((totalCap * capacityPct) / 100 * whFactor)
  const todayOrders = randInt(rng, 900, 1800)
  const inboundDone = randInt(rng, 110, 160), inboundPlan = 150
  const outboundDone = randInt(rng, 80, 130), outboundPlan = 120
  const kpis: OverviewKpi[] = [
    { label: '库存周转率', value: turnoverRate.toFixed(1), unit: '次/月', trend: rng() > 0.3 ? 'up' : 'down', trendVal: randRange(rng, 3, 15).toFixed(1), icon: 'blue' },
    { label: '库容使用率', value: capacityPct, unit: '%', progress: capacityPct, sub: `${fmt(totalStock)} / ${fmt(Math.round(totalCap * whFactor))} 件`, icon: 'cyan' },
    { label: '今日订单量', value: fmt(todayOrders), unit: '单', trend: 'up', trendVal: randRange(rng, 5, 18).toFixed(1), icon: 'green' },
    { label: '作业效率', rows: [{ name: '入库', done: inboundDone, plan: inboundPlan }, { name: '出库', done: outboundDone, plan: outboundPlan }], sub: '完成量 / 计划量', icon: 'orange' },
  ]

  const todayIn = randInt(rng, 80, 180)
  const todayOut = randInt(rng, 60, 140)
  const lowStockCount = randInt(rng, 6, 18)
  const stats: OverviewStat[] = [
    { label: '今日入库单', value: fmt(todayIn), gradient: ['#1a5cb0', '#3a8de0'], type: 'inbound' },
    { label: '今日出库单', value: fmt(todayOut), gradient: ['#3a7a3f', '#6ba84f'], type: 'outbound' },
    { label: '库存总量(件)', value: fmt(totalStock), gradient: ['#1a6a8a', '#3a9ec0'] },
    { label: '低库存商品', value: lowStockCount, gradient: ['#a82828', '#d44848'], type: 'lowstock' },
  ]

  const trend = { labels, inbound: [] as number[], outbound: [] as number[] }
  for (let i = 0; i < days; i++) { trend.inbound.push(randInt(rng, 60, 150)); trend.outbound.push(randInt(rng, 40, 120)) }

  const orderStatus = [
    { name: '待处理', value: randInt(rng, 40, 80), color: BI_THEME.orange },
    { name: '进行中', value: randInt(rng, 60, 100), color: BI_THEME.blue },
    { name: '已完成', value: randInt(rng, 200, 320), color: BI_THEME.green },
    { name: '已取消', value: randInt(rng, 10, 30), color: BI_THEME.grey },
  ]

  const whInventory = whs.map((w) => {
    const base = randInt(rng, 4000, 14000)
    const available = Math.round(base * randRange(rng, 0.82, 0.92))
    return { name: w.name, available, locked: base - available }
  }).sort((a, b) => b.available + b.locked - (a.available + a.locked))

  const alerts: OverviewAlert[] = []
  const usedSkus = new Set<string>()
  for (let i = 0; i < 6; i++) {
    let sku: [string, string]
    do { sku = pickItem(rng, SKU_POOL) } while (usedSkus.has(sku[1]))
    usedSkus.add(sku[1])
    const isLowStock = rng() > 0.35
    const wh = pickItem(rng, whs)
    alerts.push({
      level: isLowStock ? 'danger' : 'warning',
      tag: isLowStock ? '低库存' : '临期',
      title: sku[0], sku: sku[1], warehouse: wh.name,
      current: randInt(rng, 1, 12), threshold: randInt(rng, 15, 40),
      daysLeft: isLowStock ? 0 : randInt(rng, 3, 30), price: randInt(rng, 80, 12000),
    })
  }

  const todoTpl: { t: string; color: string; tfmt: (n: number) => string }[] = [
    { t: '入库审核', color: BI_THEME.orange, tfmt: (n) => `${n} 张入库单待审核` },
    { t: '出库发货', color: BI_THEME.red, tfmt: (n) => `${n} 张出库单待发货` },
    { t: '波次拣货', color: BI_THEME.blue, tfmt: (n) => `${n} 个波次待拣货` },
    { t: '盘点', color: BI_THEME.purple, tfmt: () => '月末盘点任务待执行' },
    { t: '公告', color: BI_THEME.green, tfmt: () => '系统升级公告待确认' },
    { t: '移库', color: BI_THEME.cyan, tfmt: (n) => `${n} 个移库申请待审批` },
  ]
  const todoCount = randInt(rng, 5, 7)
  const todoTime = ['10 分钟前', '32 分钟前', '1 小时前', '2 小时前', '今天早上', '昨天']
  const todos: OverviewTodo[] = []
  for (let i = 0; i < todoCount; i++) {
    const tpl = todoTpl[i % todoTpl.length]
    const wh = pickItem(rng, whs)
    const descMap: Record<string, string> = {
      入库审核: `${wh.name} · 供应商：${pickItem(rng, VENDORS)}`,
      出库发货: `${wh.name} · 客户：${pickItem(rng, CUSTOMERS)}`,
      波次拣货: `波次号 WAVE-${String(i + 1).padStart(2, '0')}`,
      盘点: `${whs.length > 1 ? '全部仓库' : whs[0]?.name ?? '—'} · 计划 本月底 执行`,
      公告: 'v1.2.0 将于本周六凌晨停机维护',
      移库: `${wh.name} · 移库在途`,
    }
    todos.push({ tagText: tpl.t, title: tpl.tfmt(randInt(rng, 2, 8)), desc: descMap[tpl.t], time: todoTime[Math.min(i, 5)], color: tpl.color })
  }

  return { kpis, stats, trend, orderStatus, whInventory, alerts, todos }
}

/* ============ Inventory Analysis ============ */
function mockInventory(state: BiState): InventoryData {
  const rng = mulberry32(getSeed('inventory', state))
  const whs = activeWarehouses(state)
  const nSku = 50
  const skus: { name: string; sku: string; qty: number; price: number; amount: number }[] = []
  for (let i = 0; i < nSku; i++) {
    const sp = SKU_POOL[i % SKU_POOL.length]
    const qty = randInt(rng, 5, 8000)
    const price = randInt(rng, 50, 15000)
    skus.push({ name: sp[0], sku: `${sp[1]}-${i}`, qty, price, amount: qty * price })
  }
  skus.sort((a, b) => b.qty - a.qty)
  const skuTop10 = skus.slice(0, 10).map((s) => ({ sku: s.sku, name: s.name, qty: s.qty, pct: (s.qty / skus[0].qty) * 100 }))
  const lowStockList = [...skus].sort((a, b) => a.qty - b.qty).slice(0, 10).map((s) => ({ name: s.name, qty: s.qty }))

  const ageRanges = [
    { range: '<30天', color: BI_THEME.green },
    { range: '30-90天', color: BI_THEME.blue },
    { range: '90-180天', color: BI_THEME.cyan },
    { range: '180-365天', color: BI_THEME.orange },
    { range: '>365天', color: BI_THEME.red },
  ]
  const agePcts = [randRange(rng, 0.3, 0.45), randRange(rng, 0.22, 0.32), randRange(rng, 0.13, 0.2), randRange(rng, 0.06, 0.12), randRange(rng, 0.02, 0.07)]
  const totalSkuAmt = skus.reduce((s, x) => s + x.amount, 0)
  const ageDistribution = ageRanges.map((r, i) => ({ range: r.range, color: r.color, skuCount: Math.round(nSku * agePcts[i]), amount: Math.round(totalSkuAmt * agePcts[i]) }))

  const batchStatus = whs.map((w) => {
    const total = randInt(rng, 80, 260)
    const normal = Math.round(total * randRange(rng, 0.6, 0.8))
    const nearExp = Math.round(total * randRange(rng, 0.06, 0.14))
    const expired = Math.round(total * randRange(rng, 0.01, 0.05))
    return { name: w.name, normal, nearExpire: nearExp, expired, frozen: total - normal - nearExp - expired }
  })

  const skusAmt = [...skus].sort((a, b) => b.amount - a.amount)
  const abcRows = skusAmt.slice(0, 24)
  const totalAmt = abcRows.reduce((s, x) => s + x.amount, 0) || 1
  let cum = 0
  const abc = abcRows.map((s) => {
    cum += s.amount
    const cpct = (cum / totalAmt) * 100
    const category: 'A' | 'B' | 'C' = cpct <= 70 ? 'A' : cpct <= 90 ? 'B' : 'C'
    return { sku: s.name.length > 14 ? s.name.slice(0, 14) + '…' : s.name, amount: s.amount, cumulativePct: cpct, category }
  })

  return { skuTop10, lowStockList, ageDistribution, batchStatus, abc }
}

/* ============ Flow Analysis ============ */
function mockFlow(state: BiState): FlowData {
  const rng = mulberry32(getSeed('flow', state))
  const labels = dateArr(30)
  const trend30 = { labels, inQty: [] as number[], outQty: [] as number[], inAmt: [] as number[], outAmt: [] as number[] }
  let totalInQty = 0, totalOutQty = 0
  labels.forEach(() => {
    const iq = randInt(rng, 600, 2400), oq = randInt(rng, 500, 2200)
    const ia = iq * randInt(rng, 180, 900), oa = oq * randInt(rng, 200, 1100)
    trend30.inQty.push(iq); trend30.outQty.push(oq); trend30.inAmt.push(ia); trend30.outAmt.push(oa)
    totalInQty += iq; totalOutQty += oq
  })
  const vendors = VENDORS.map((v) => ({ vendor: v, amount: randInt(rng, 500000, 9000000), orderCount: randInt(rng, 8, 60), onTimeRate: randRange(rng, 0.75, 0.99) }))
    .sort((a, b) => b.amount - a.amount).slice(0, 10)
  const customers = CUSTOMERS.map((c) => ({ customer: c, amount: randInt(rng, 500000, 10000000), orderCount: randInt(rng, 12, 90), returnRate: randRange(rng, 0.005, 0.11) }))
    .sort((a, b) => b.amount - a.amount).slice(0, 10)
  const retLabels = dateArr(14)
  const returnVals = retLabels.map(() => randRange(rng, 0.01, 0.075))
  const avgRetRate = returnVals.reduce((s, x) => s + x, 0) / returnVals.length
  const rrPcts = [randRange(rng, 0.3, 0.5), randRange(rng, 0.15, 0.28), randRange(rng, 0.12, 0.22), randRange(rng, 0.1, 0.22)]
  const rrTotal = rrPcts.reduce((s, x) => s + x, 0)
  const returnReasons = RETURN_REASONS.map((r, i) => ({ name: r.name, color: r.color, count: Math.round((120 * rrPcts[i]) / rrTotal) }))
  return { trend30, netIn: totalInQty, netOut: totalOutQty, netVal: totalInQty - totalOutQty, vendors, customers, returnTrend: { labels: retLabels, values: returnVals }, avgRetRate, returnReasons }
}

/* ============ Efficiency ============ */
function mockEfficiency(state: BiState): EfficiencyData {
  const rng = mulberry32(getSeed('efficiency', state))
  const workers = WORKERS.slice(0, 8)
  const dayLabels = dateArr(7)
  const workerDaily = workers.map((w) => {
    const days: number[] = []
    let total = 0
    for (let i = 0; i < 7; i++) { const q = randInt(rng, 60, 200); days.push(q); total += q }
    return { worker: w, days, avg: Math.round(total / 7) }
  })
  const avgEff = Math.round(workerDaily.reduce((s, x) => s + x.avg, 0) / workerDaily.length)
  const waveTotal = randInt(rng, 40, 70)
  const waveStatus = [
    { name: '待分配', value: randInt(rng, 2, 8), color: BI_THEME.grey },
    { name: '进行中', value: randInt(rng, 8, 16), color: BI_THEME.blue },
    { name: '已完成', value: randInt(rng, 20, 40), color: BI_THEME.green },
    { name: '超时', value: randInt(rng, 1, 5), color: BI_THEME.red },
  ]
  const waveDone = waveStatus.find((x) => x.name === '已完成')?.value ?? 0
  const wavePct = Math.round((waveDone / waveTotal) * 100)
  const durationTypes = [
    { type: '入库', p10: 15, p25: 22, p50: 32, p75: 45, p90: 65, color: BI_THEME.blue },
    { type: '出库', p10: 12, p25: 19, p50: 28, p75: 42, p90: 70, color: BI_THEME.green },
    { type: '盘点', p10: 40, p25: 55, p50: 80, p75: 120, p90: 180, color: BI_THEME.orange },
  ].map((d) => {
    const j = () => randRange(rng, 0.88, 1.14)
    return { ...d, p10: Math.round(d.p10 * j()), p25: Math.round(d.p25 * j()), p50: Math.round(d.p50 * j()), p75: Math.round(d.p75 * j()), p90: Math.round(d.p90 * j()) }
  })
  const types = ['入库', '出库', '盘点']
  const tPrefixes: Record<string, string> = { 入库: 'RK', 出库: 'CK', 盘点: 'PD' }
  const statuses = [
    { s: '进行中', range: [20, 85] },
    { s: '已完成', range: [100, 100] },
    { s: '超时', range: [40, 95] },
    { s: '待开始', range: [0, 0] },
  ]
  const tasks: EfficiencyTask[] = []
  for (let i = 0; i < 22; i++) {
    const type = types[Math.floor(rng() * types.length)]
    const st = statuses[Math.floor(rng() * statuses.length)]
    const h = randInt(rng, 6, 17), m = String(randInt(rng, 0, 59)).padStart(2, '0')
    tasks.push({
      no: `${tPrefixes[type]}260902${String(i + 1).padStart(3, '0')}`,
      type, worker: pickItem(rng, workers), startTime: `${String(h).padStart(2, '0')}:${m}`,
      progress: randInt(rng, st.range[0], st.range[1]), status: st.s,
    })
  }
  return { workerDaily, dayLabels, avgEff, waveStatus, wavePct, waveTotal, durationTypes, tasks, taskTotal: tasks.length }
}

/* ============ 统一入口 ============ */
export function generateBiData(view: 'overview', state: BiState): OverviewData
export function generateBiData(view: 'inventory', state: BiState): InventoryData
export function generateBiData(view: 'flow', state: BiState): FlowData
export function generateBiData(view: 'efficiency', state: BiState): EfficiencyData
export function generateBiData(view: BiView, state: BiState) {
  switch (view) {
    case 'overview': return mockOverview(state)
    case 'inventory': return mockInventory(state)
    case 'flow': return mockFlow(state)
    case 'efficiency': return mockEfficiency(state)
  }
}

export const BI_FMT = fmt
