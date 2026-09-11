## Why

当前 WMS 项目的 Vue 前端采用传统侧边栏管理后台风格，视觉表现较为普通。已有的 Apple Store 风格静态预览页（`preview/apple-store-wms.html`）设计优秀，玻璃拟态（Glassmorphism）+ 顶部栏/侧边栏/底部 Dock 的 macOS 风格布局非常现代化，但目前仅是纯静态展示：图表用纯 CSS 绘制无法交互、无法切换时间维度、无多页面板切换、无点击下钻能力。用户需要一个**可交互、带 Mock 数据、可快速落地**的 BI 数据看板原型，用于评估 Apple Store 风格是否适合整体 UI 重构方向，同时可作为演示 Demo 使用。

## What Changes

- 在 `preview/apple-store-wms.html` 基础上增强为可交互 BI 看板（保留单文件结构，无构建链）
- 集成 Chart.js CDN 替代原纯 CSS 图表，实现柱状图/折线图/环形图/堆叠条形图的 tooltip、图例切换、动画交互
- 新增 Mock 数据层：KPI、出入库趋势、单据分布、仓库库存、预警、待办等全部使用随机可复现数据生成，支持时间范围切换后重新生成
- 新增全局筛选器：时间范围（今日/近7天/近30天/自定义）+ 仓库选择，筛选后所有 KPI 和图表联动刷新
- 实现多面板切换：点击侧边栏切换主内容区（数据看板 / 库存分析 / 出入库分析 / 作业效率 四大 BI 视图）
- 新增图表交互：点击 KPI 卡可展开下钻详情、点击库存预警可弹出 SKU 明细弹窗
- 新增导出功能：支持导出当前看板为 PNG 截图（html2canvas CDN）

## Capabilities

### New Capabilities
- `bi-dashboard/overview`：数据总览面板 — KPI 核心指标卡、统计彩色卡、出入库趋势图、单据状态环形图、仓库库存分布、库存预警列表、待办事项网格，支持全局筛选联动
- `bi-dashboard/inventory-analysis`：库存分析面板 — SKU 库存 Top10/低库存排行、库龄分析、批次状态分布、ABC 分类帕累托图
- `bi-dashboard/flow-analysis`：出入库分析面板 — 30天出入库趋势折线图、出入库对比、供应商入库TOP、客户出库TOP、退货率分析
- `bi-dashboard/efficiency`：作业效率面板 — 每人每日拣货量柱状图、波次完成率、作业时效箱线图、入库/出库/盘点任务进度表
- `bi-dashboard/common-filters`：全局筛选与通用交互 — 时间范围筛选器、仓库筛选器、图表联动刷新、弹窗下钻、PNG 导出

### Modified Capabilities
（无，此变更为新增独立静态 BI 原型，不修改现有 Vue 项目或后端的任何行为规范）

## Impact

- **新增/修改文件**：仅 `preview/apple-store-wms.html`（大幅增强），不影响 `frontend-vue/` 和 `backend-python/`
- **新增 CDN 依赖**：Chart.js、html2canvas（通过 `<script src="https://cdn...">` 引入，不增加本地依赖）
- **零构建链**：单 HTML 文件，浏览器直接打开即可运行，无需 npm/Vite/Webpack
- **与现有项目解耦**：此 BI 为独立原型验证，若效果满意后可再迁移到 Vue 项目中
