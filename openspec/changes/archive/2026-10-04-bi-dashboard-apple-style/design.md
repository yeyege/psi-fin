## Context

See [proposal.md](proposal.md) for motivation. 技术约束如下：

- 当前 `preview/apple-store-wms.html` 是单文件静态页（CSS + 内联 JS + Mock 数据常量），约 1000 行，无构建链、无外部依赖
- 用户需求是"快速出可交互 BI 原型"，目标是**半天可交付**、浏览器直接打开即可使用
- 不得修改 `frontend-vue/` 和 `backend-python/` 下的任何代码（保持现有系统零侵入）

## Goals / Non-Goals

**Goals:**
- 4 个 BI 视图 + 全局筛选器 + 交互下钻 + 截图导出，全部在单一 HTML 文件内完成
- 所有可视化使用 Chart.js（CDN），保证 hover tooltip、图例切换、动画开箱即用
- 所有数据由纯 JS Mock 层生成，无网络请求，保证离线可用 + 筛选响应 < 300ms
- 保留并复用 Apple Store 风格视觉变量（--blue / --green / --blur / --radius-lg 等）与布局结构（topbar / sidebar / main / dock）

**Non-Goals:**
- **不做**真实后端 API 对接（现阶段纯 Mock 原型）
- **不做**用户登录/权限校验
- **不做**数据持久化（刷新后重置）
- **不做**移动端响应式（现有 @media 断点保持即可，不额外优化手机端）
- **不迁移**到 Vue 项目（若此原型通过评审，再通过后续 change 单独迁移）

## Decisions

### D1: 单 HTML 文件 vs 多文件拆分

**决策：保持单一 HTML 文件，内联 `<style>` 与 `<script>`**

- 理由：符合"快速"目标，单文件双击即可运行，无需 server 即可展示，避免相对路径问题
- 备选：拆分为 bi.html + bi.css + bi.js + mock.js → 增加路径依赖与本地 server 要求，放弃

### D2: 图表库选择：Chart.js vs ECharts

**决策：Chart.js 4.x（CDN：`https://cdn.jsdelivr.net/npm/chart.js`）**

- 理由：Chart.js 包体更小（~200KB vs ECharts ~700KB）、API 更简单、默认样式更接近 Apple 简洁风、柱状图/折线图/环形图/箱线图全部内置支持（箱线图可用 `chartjs-chart-boxplot` 插件或用 bar chart 手动模拟）
- 备选：ECharts → 功能更强大但配置复杂，暂不需要地理热力图/桑基图等高级图表

### D3: Mock 数据生成策略

**决策：纯函数 + 可复现伪随机（seeded random）**

```
generateMockData(timeRange, warehouseIds) → { kpis, trendData, donutData, alerts, ... }
```

- 使用 `mulberry32` seeded PRNG，seed = hash(timeRange + sorted(warehouseIds))，保证相同筛选条件下数据稳定（不反复横跳），又在筛选变更时产生合理差异
- 生成器按各 BI 视图分模块：`mockOverview()` / `mockInventory()` / `mockFlow()` / `mockEfficiency()`，避免单函数过大
- 仓库集合：`[{id:'sh',name:'上海仓'}, {id:'gz',name:'广州仓'}, ...]` 固定 5 个，Mock 函数按 ID 过滤聚合

### D4: 多视图切换实现

**决策：DOM 级显示/隐藏 + 单一页面状态对象**

- 结构：`<main>` 内部放置 4 个 `<section class="page page-XXX">`，默认仅 `page-overview` 显示，其余 `display:none`
- 全局状态对象 `window.BI_STATE = { timeRange, warehouses, activePage, loadingMap }`，统一管理
- 侧边栏/Dock 点击 → 修改 `BI_STATE.activePage` → 切换显示 → 若该页面首次加载则调用对应 `renderXxxChart(BI_STATE)` 初始化图表

### D5: Modal 组件实现

**决策：单一全局 Modal DOM，内容函数注入**

```html
<div id="modal" class="modal hidden"><div class="modal-content"><div id="modal-body"></div></div></div>
```

- 提供 API：`openModal(title, renderFn)` / `closeModal()`，renderFn 返回 HTML 字符串或 DOM
- 遮罩点击 + ESC 监听绑定一次，不复绑

### D6: 截图导出实现

**决策：html2canvas CDN，导出主内容区节点**

- CDN：`https://cdn.jsdelivr.net/npm/html2canvas`
- 导出节点：`<main class="main">`（或当前 page section），scale=2 保证高清
- 文件名模板：`WMS-BI-{pageName}-{yyyyMMddHHmmss}.png`

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|---|---|---|
| CDN 不可达（离线或内网环境） | Chart.js/html2canvas 加载失败 → 白屏图表区 | 在 `<head>` 增加 `<script>` onerror 回退：若 3 秒未加载，降级回原纯 CSS 图表（保留原代码段），导出按钮隐藏 |
| 单文件过长（可能 >3000 行） | 可维护性下降 | Mock 层与渲染层按 IIFE 模块严格分块，每块前加清晰 Banner 注释 `/* ===== Module: Overview ===== */`，行内注释不超过 1:20 |
| Chart.js 与原有 CSS 变量脱节 | 图表色与卡片色不一致 | 提取 `const THEME_COLORS = { blue:'#0071e3', green:'#34c759', ... }` 与 `:root` CSS 变量一一对应，所有 Chart dataset 从此常量取色 |
| 筛选器与图表刷新闪屏 | 用户体验差 | 刷新时先调用 `chartInstance.data = newData` 再 `chart.update('none')`，不销毁重建；图表容器 loading 用 CSS `::after` overlay，不阻塞 DOM |
| Modal 内渲染复杂图表性能差 | 打开 Modal 卡顿 | Modal 内仅展示表格与小型 sparkline（5 个数据点以下），不渲染大图表 |
