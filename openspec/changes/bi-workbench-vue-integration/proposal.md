## Why

`bi-dashboard-apple-style` change 已交付一份视觉丰富、交互完整的 Apple 风格 BI 原型（`apple-store-wms.html`），但它是**游离于应用之外的单文件静态页**：不挂导航、不进构建、无法作为产品一级能力演示。与此同时 Vue 应用内的两块「看板」质量参差——[ExecutiveView.vue](file:///d:/wms-test/frontend-vue/src/views/ExecutiveView.vue)（经营驾驶舱）只有 3 张财务图表，信息量薄；[DashboardView.vue](file:///d:/wms-test/frontend-vue/src/views/DashboardView.vue)（仓储看板）虽有 1555 行 6 图，但几乎全是 Mock 且无 Apple 质感、无多面板切换、无下钻。用户评估产品时看到的是「一个精美静态原型 + 两个割裂的应用内看板」三块互不相通。

需要把原型的 Apple BI 体验**工程化进 Vue**：做成一级可导航、自带面板切换的全幅 BI 工作台，并把薄弱的财务驾驶舱并入其中，形成统一的「看数」心智入口。当前**无真实数据**，故整条链路以 Mock 落地，前端零后端依赖。

## What Changes

- 新增全幅 BI 工作台路由 `/bi`：复刻原型的 Apple 布局（顶栏 + 分段 Dock + 主内容区），四个仓储面板 + 一个财务面板在工作台内部切换，主站 Element 布局不受影响。
- 四个 Mock 仓储面板：**数据总览 / 库存分析 / 出入库分析 / 作业效率**，图表从原型的 Chart.js **翻译为项目已有依赖 ECharts（echarts@6）**，不引入第二套图表库。
- **并入现有财务 Executive**：将驾驶舱作为 `/bi` 内的「经营财务」面板复用其既有 `/api/executive/*` 真数据（口径不变），`/executive` 路由重定向到 `/bi`，侧边栏「经营驾驶舱」组入口指向 `/bi`。
- 新增 `src/components/BiChart.vue`：统一 ECharts 容器（init/setOption/resize/dispose + Apple 调色常量注入），消除现有 Executive/Dashboard 中重复的命令式图表样板。
- 新增 `src/composables/useBiState.ts`：全局筛选状态（时间范围 + 仓库 + 当前面板），驱动面板联动刷新。
- 新增 `src/api/mock/bi.ts`：移植原型 seeded PRNG（`mulberry32` + `hashString`）与四大视图生成器，`generateBiData(view, state)` 纯函数直接 import（**不经 axios mockAdapter**，BI 永不发网络请求）。
- 新增 `src/styles/bi-apple.css`：以 `.bi-scope` 作用域隔离的 Apple 设计变量，仅在工作台内生效。
- 导出：面板图表级 PNG 通过 `echarts.getInstanceByDom().getDataURL()` 实现；整页截图（原型用 html2canvas）**本 change 暂不做**，避免新增依赖。

## Capabilities

### New Capabilities

- `bi-workbench/shell`: 全幅 `/bi` 工作台外壳——Apple 局部主题隔离、分段 Dock 面板切换、全局时间/仓库筛选联动、下钻 Modal、图表级导出、财务面板复用与 `/executive` 重定向、`BiChart.vue` 容器契约。
- `bi-workbench/mock-data`: Mock 数据层——seeded 可复现伪随机、`generateBiData(view, state)` 分视图纯函数、各面板返回结构契约、直接 import 不走网络、可复现性单测锁定。
- `bi-workbench/overview`: 数据总览面板——KPI 卡、统计彩色卡、出入库趋势、单据状态环形、仓库库存堆叠、库存预警列表 + 下钻、待办网格。
- `bi-workbench/inventory-analysis`: 库存分析面板——SKU 高/低库存 TOP10、库龄分布、批次状态堆叠、ABC 帕累托。
- `bi-workbench/flow-analysis`: 出入库分析面板——30 天出入库趋势、净增减、供应商入库 TOP10、客户出库 TOP10、退货率趋势与原因分布。
- `bi-workbench/efficiency`: 作业效率面板——人员日拣货量、波次完成率、作业时效箱线图、任务进度表。

### Modified Capabilities

（无 API 级需求变更。`finance/executive-dashboard` 仅**呈现宿主**由独立路由 `/executive` 改为 `/bi` 内的「经营财务」面板，其数据返回契约与「口径一致可核对」要求保持不变，详见 Impact。）

## Impact

- **纯前端，零后端改动**：不新增任何 `backend-python` 端点或聚合服务；作业效率面板 Mock 造数，**不改业务模型、不加时间戳字段**。
- **新增文件**：`views/BiWorkbenchView.vue`（+ 各面板子组件）、`components/BiChart.vue`、`composables/useBiState.ts`、`api/mock/bi.ts`、`styles/bi-apple.css`。
- **修改文件**：`router/index.ts`（新增 `/bi`、`/executive → /bi` 重定向）、`App.vue`（驾驶舱组入口指向 `/bi`）、`ExecutiveView.vue`（其渲染逻辑迁移为工作台财务面板子组件，数据源不变）。
- **依赖**：`echarts@6` 已是依赖，无新增运行时依赖；不移植原型的 Chart.js / html2canvas CDN。
- **既有仓储看板 `/dashboard` 保持不动**：它与新 `/bi` overview 的重叠收敛列为后续（本 change 非目标，避免范围膨胀）。
- **真实数据演进路径**：后续接真后端时，仓储面板切到未来 `/api/bi/*`；库存分析面板的库龄/批次状态将复用 `p0-2-strict-fifo-expiry` 将新增的 `ageDays / batchStatus` 字段——**两 change 解耦、并行、互不阻塞**。
- **GitHub Pages 演示**：Mock 模式下工作台照常可交互，演示不退化。
- **测试**：`vitest` 锁 `bi.ts` 可复现性与返回结构；`BiChart.vue` 冒烟；`npx vue-tsc --noEmit` 类型通过；`npm run build` 成功。
