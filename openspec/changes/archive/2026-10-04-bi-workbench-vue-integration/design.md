## Context

See [proposal.md](proposal.md) — Why。落地前的技术现状：

- 前端依赖：[package.json](file:///d:/wms-test/frontend-vue/package.json) 已含 `echarts@^6.1.0`；**无** Chart.js、**无** html2canvas。原型 [apple-store-wms.html](file:///d:/wms-test/apple-store-wms.html) 用 Chart.js + html2canvas CDN。
- Mock 机制：[client.ts](file:///d:/wms-test/frontend-vue/src/api/client.ts) 在 `VITE_USE_MOCK==='true'` 时把 `mockAdapter`（[src/api/mock/index.ts](file:///d:/wms-test/frontend-vue/src/api/mock/index.ts)）挂为 axios adapter，按 REST path 拦截。BI 面板**永不发网络请求**，故其数据不走该 adapter。
- 既有看板：[ExecutiveView.vue](file:///d:/wms-test/frontend-vue/src/views/ExecutiveView.vue) 用 ECharts + 真接口 `/api/executive/*`（[executive.py](file:///d:/wms-test/backend-python/app/routers/executive.py)），有严格「口径一致」要求（[finance/executive-dashboard spec](file:///d:/wms-test/openspec/specs/finance/executive-dashboard/spec.md)）；[DashboardView.vue](file:///d:/wms-test/frontend-vue/src/views/DashboardView.vue) 1555 行、6 图基本 Mock。两处各自重复 init/resize/dispose 样板。
- 导航：[router/index.ts](file:///d:/wms-test/frontend-vue/src/router/index.ts) 扁平 hash 路由；[App.vue](file:///d:/wms-test/frontend-vue/src/App.vue) 侧边栏「经营驾驶舱」组含 `/executive`、`/dashboard`。
- 原型交互资产：`BI_STATE`、`mulberry32`、四大 `mockXxx()` 生成器、分段页面切换、Modal 下钻、导出——已在 `apple-store-wms.html` 中验证可用（见 `bi-dashboard-apple-style` tasks 全绿）。

## Goals / Non-Goals

**Goals:**
- 以最小侵入把原型 Apple BI 体验做成 `/bi` 一级工作台，4 个 Mock 仓储面板 + 1 个复用真数据的财务面板，内部 Dock 切换。
- 图表统一到 ECharts，抽 `BiChart.vue` 复用容器；Apple 主题用 `.bi-scope` 局部隔离，不动主站。
- Mock 数据可复现（同筛选条件稳定不跳变），并保证 GitHub Pages 演示交互完整。
- 财务驾驶舱并入后口径不回退。

**Non-Goals:**
- 不做后端 `/api/bi/*` 聚合、不改业务模型、不加作业时间戳字段（接真数据属后续 change）。
- 不重构/下线 `/dashboard` 仓储看板（其与 overview 的收敛列为后续）。
- 不做整页截图导出（不引 html2canvas）；不做移动端额外响应式优化。
- 不迁移原型单文件本身（原型保留作静态演示，本 change 是「在 Vue 内重建」而非「嵌入 iframe」）。

## Decisions

### D1: 单个全幅工作台 `/bi`（内部 Dock 切换）vs 4 个独立侧边栏路由

**决策：单一路由 `/bi` 承载全幅工作台，四+一面板在工作台内以分段 Dock 切换。**

- 理由：原型价值在于自带 topbar/侧边/Dock 的 Apple 沉浸布局；拆成 4 条 Element 风格路由会把这份质感打散，并与 `/dashboard`、`/executive` 形成三块导航重叠。单入口最贴近「重构薄弱的驾驶舱」诉求。
- 备选：4 个 `/bi/*` 路由挂侧边栏 → 导航重叠、Apple 外壳丢失，放弃。
- 备选：iframe 直接嵌原型 → 双运行时、无法用项目 ECharts/主题、不可维护，放弃。

### D2: Apple 主题以 `.bi-scope` 作用域隔离

**决策：新建 `src/styles/bi-apple.css`，所有 Apple 设计变量与布局样式挂在 `.bi-scope` 根类下，仅 `BiWorkbenchView` 引入。**

- 理由：锁定「BI 页局部 Apple 主题、主站仍 Element Plus」的既定取向；避免全局 `:root` 变量污染 Element 主题与既有 19 页。
- 变量沿用原型：`--blue:#0071e3 / --green:#34c759 / --orange / --red / --purple / --radius-lg / --blur` 等。

### D3: Chart.js → ECharts，统一 `BiChart.vue` 容器

**决策：不引入 Chart.js；所有原型图表翻译为 ECharts option。抽 `src/components/BiChart.vue`：props 收 `option`，内部 `echarts.init` + `setOption`（`notMerge` 由筛选刷新策略决定）+ `ResizeObserver`/window resize + `onBeforeUnmount dispose`；对外暴露 `getDataURL()` 与 `getInstance()`。Apple 调色以常量注入 series。**

- 理由：复用既有依赖与 Executive/Dashboard 先例，消除重复样板；Chart.js 与 ECharts 混用会双份打包。
- 图表映射：bar/line/doughnut/pie 直接映射；ABC 帕累托用 bar + line 双 Y 轴；时效箱线用 ECharts `boxplot`；净增减仪表盘用纯 CSS + 数字（与原型一致）。

### D4: Mock 数据层——seeded 纯函数，直接 import 不走 adapter

**决策：`src/api/mock/bi.ts` 移植 `mulberry32(seed)` + `hashString(str)`，`seed = hash(timeRange.preset + start + end + sorted(warehouses).join())`；导出 `generateBiData(view, state)` 分派到 `mockOverview/mockInventory/mockFlow/mockEfficiency`，各返回**强类型**结构（沿用原型字段命名，camelCase）。`useBiState` 变更时面板直接调用该纯函数重算，不注册进 `mockAdapter` 路径表。**

- 理由：BI 无真实端点，走 adapter 反而要伪造 REST path、增加心智；纯函数最简、可单测。seeded 保证筛选不变时数据不横跳。
- 备选：塞进 mockAdapter 按 `/api/bi/*` 拦截 → 为不存在的端点编路径、且 adapter 是同步替换 axios 异步链路，收益为零，放弃。

### D5: 财务 Executive 作为「经营财务」面板并入，数据源不变

**决策：把 ExecutiveView 的渲染逻辑迁移为 `BiFinancePanel.vue`，仍调用现有 `/api/executive/*`（真接口 / Pages 下走 mockAdapter），图表改用 `BiChart.vue` 承载、外观套 `.bi-scope`；`/executive` 路由改为重定向到 `/bi`（默认落财务面板或 overview）。**

- 理由：满足「并入 Executive」，同时不违背 `finance/executive-dashboard` 的「口径一致可核对」——数据源与计算保持原样，只换呈现宿主。
- 明确：工作台内**财务面板用真/同口径数据，四个仓储面板用 `bi.ts` Mock**，二者数据来源在 UI 上以面板标题或角标区分，避免误读。

### D6: 作业效率面板整体 Mock，不动业务模型

**决策：效率面板四图全部由 `mockEfficiency(state)` 造数（人均拣货、波次完成率、耗时 P10–P90 箱线、任务进度表），不依赖 `operator_id/started_at/finished_at`。**

- 理由：Mock 阶段无需真实时间戳；与 `p0-2` 及未来「效率采集」解耦、并行、互不阻塞。接真数据时再单独 change 扩模型。

### D7: 导出仅图表级 PNG

**决策：每面板「导出」按钮调用当前各 `BiChart` 实例 `getDataURL({ pixelRatio:2, backgroundColor:'#fff' })` 下载；整页拼图（需 html2canvas）列为后续，不在本 change。**

- 理由：零新依赖即拿到可用的「出图」演示能力；整页截图对布局一致性要求高、收益有限。

## Risks / Trade-offs

- [`/bi` overview 与 `/dashboard` 仓储看板重叠，用户见两个「看板」] → 本 change 不动 `/dashboard`，在 proposal/NOTES 标注为后续收敛项；侧边栏「经营驾驶舱」组以 `/bi` 为主入口降低割裂感。
- [工作台内混合 Mock（仓储）与真数据（财务）造成误读] → D5：面板级数据来源标注；仓储面板 Mock 明确以「演示数据」角标提示。
- [ECharts 还原原型观感有差异（Chart.js 默认更“轻”）] → 以 `.bi-scope` 统一配色 + `BiChart` 默认 option（去网格线、圆角柱、Apple 字号）对齐；差异可接受。
- [`.bi-scope` 若选择器泄漏影响主站] → 全部规则以 `.bi-scope` 前缀限定，禁止裸元素选择器；构建后人工抽查主站若干页样式不变。
- [ExecutiveView 迁移为面板引入回归] → 保留其 `onBeforeUnmount` dispose 语义迁入 `BiChart`；`vue-tsc` + 手动冒烟覆盖 `/executive → /bi` 与财务数值一致性。

## Migration Plan

- 纯前端增量，无数据/接口迁移。回滚 = 移除 `/bi` 路由 + 还原 `App.vue`/`router`/`ExecutiveView` 引用，即恢复旧驾驶舱与原型链接。
- 建议合并顺序：① `bi.ts` + 可复现性单测 → ② `BiChart.vue` + `useBiState` + `bi-apple.css` → ③ `BiWorkbenchView` 外壳与 Dock/重定向 → ④ 四仓储面板 → ⑤ 财务面板并入 → ⑥ 全量 `vue-tsc`/`vitest`/`build` 回归。

## Open Questions

- 是否最终以下线 `/dashboard` 仓储看板、统一并入 `/bi` 为目标？（本 change 先并存）
- 是否需要整页 PNG 导出（引入 html2canvas）留待演示反馈决定。
- Dock 面板命名与顺序（是否把「经营财务」置顶为默认面板）待 UI 走查确认。
