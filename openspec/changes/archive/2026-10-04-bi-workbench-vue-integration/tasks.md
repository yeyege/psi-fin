## 1. Mock 数据层（`src/api/mock/bi.ts`）

- [x] 1.1 移植 `mulberry32(seed)` 与 `hashString(str)`；实现 `buildSeed(state)` = `hash(timeRange.preset + start + end + sortedWarehouses.join('|'))`。定义各面板返回的 TS 接口（`OverviewData / InventoryData / FlowData / EfficiencyData`，字段名沿用原型 camelCase）。验证：`npx vue-tsc --noEmit` 无类型错误
- [x] 1.2 实现 `mockOverview/mockInventoryAnalysis/mockFlowAnalysis/mockEfficiency(state)` 四个纯生成器，`state={timeRange,warehouses}`；`generateBiData(view,state)` 分派。数值范围对齐原型（如库容使用率 50~95%、退货率 1%~8%、人均拣货 50~200 件/天、ABC 金额约 70/20/10）。验证：新增 `src/api/mock/bi.test.ts` 用例通过
- [x] 1.3 可复现性单测：同一 `state` 两次 `generateBiData` 深度相等；不同 `timeRange`/仓库集合产生不同数据。验证：`npx vitest run src/api/mock/bi.test.ts` 通过

## 2. 通用件：主题 + 筛选状态 + 图表容器

- [x] 2.1 新建 `src/styles/bi-apple.css`，把原型 `:root` 设计变量与 topbar/dock/card/modal 等布局样式全部收敛到 `.bi-scope` 前缀下（禁止裸元素选择器）。仅在工作台根节点加 `.bi-scope`。验证：构建后抽查主站若干页（库存/销售/用户）样式无变化
- [x] 2.2 新建 `src/composables/useBiState.ts`：持 `{ timeRange:{preset,start,end}, warehouses:string[], activePanel }`，暴露 `applyFilters()` 与当前 seed 重算入口；`activePanel ∈ overview|inventory|flow|efficiency|finance`。验证：切换筛选/面板时状态值正确，`vue-tsc` 通过
- [x] 2.3 新建 `src/components/BiChart.vue`：props `option`，内部 `echarts.init`、`setOption`、`ResizeObserver`+window resize、`onBeforeUnmount` 自动 `dispose`；`defineExpose({ getDataURL, getInstance })`；内置 Apple 调色常量并合并进 option。验证：在任一面板渲染一张柱图，缩放窗口自适应、离页无内存泄漏告警

## 3. 工作台外壳（`BiWorkbenchView.vue` + 路由/导航）

- [x] 3.1 新建 `src/views/BiWorkbenchView.vue`：根节点 `.bi-scope`，含顶栏（标题 + 时间范围 4 预设 + 自定义日期 + 仓库多选 chip + 导出按钮）、分段 Dock（数据总览/库存分析/出入库分析/作业效率/经营财务 五项）、主内容区面板插槽，默认显示 overview。验证：打开 `/bi` 无 console error，Dock 五面板可切换、激活态联动、筛选态跨面板保持
- [x] 3.2 `router/index.ts`：新增 `{ path:'/bi', ... BiWorkbenchView }`；把原 `/executive` 改为 `redirect:'/bi'`。`App.vue` 侧边栏「经营驾驶舱」组：`/executive` 项改为指向 `/bi`（文案「BI 工作台」），保留 `/dashboard` 仓储看板项不动。验证：点击侧边栏进入 `/bi`；旧 `#/executive` 自动跳 `#/bi`
- [x] 3.3 联动刷新：`useBiState` 变更 → 非财务面板重算 `generateBiData`、`BiChart` 以 `setOption(newOption)`（`notMerge:false` 平滑过渡）刷新，期间显示 CSS loading 遮罩不销毁重建。验证：切筛选 300ms 内更新、无白屏闪烁

## 4. 四个 Mock 仓储面板

- [x] 4.1 `BiOverviewPanel.vue`：KPI 卡（库存周转/库容使用率/今日订单/作业效率）+ 4 彩色统计卡（入库/出库/库存总量/低库存，点击跳出入库面板）+ 出入库趋势柱（ECharts bar）+ 单据状态环形（doughnut→ECharts pie 中心总数）+ 仓库库存堆叠水平条 + 库存预警列表（点击开 Modal 下钻：分仓分布 + 7 天迷你趋势）+ 待办网格。数据源 `generateBiData('overview',state)`。验证：各元素渲染、下钻 Modal 打开/关闭、彩色卡跳面板均正常
- [x] 4.2 `BiInventoryPanel.vue`：SKU 高/低库存 TOP10 并排水平条 + 库龄分布饼（5 段）+ 批次状态按仓库堆叠柱（正常/临期/过期/冻结）+ ABC 帕累托（bar+line 双 Y 轴，70/90/100% 分割线）。数据源 `generateBiData('inventory',state)`。验证：仓库筛选变更时 TOP10 重算，帕累托 tooltip 含分类与累计占比
- [x] 4.3 `BiFlowPanel.vue`：30 天出入库双折线（数量/金额切换 + `dataZoom` 框选缩放与重置）+ 净增减仪表盘（纯 CSS 数字）+ 供应商入库 TOP10 水平条（含准时率进度条）+ 客户出库 TOP10 水平条（含退货率进度条）+ 退货率折线 + 退货原因环形（>5% 顶部红色警示条）。数据源 `generateBiData('flow',state)`。验证：指标切换、缩放重置、警示条按阈值显隐
- [x] 4.4 `BiEfficiencyPanel.vue`：人员 7 天分组柱状图（顶部「人均日拣货 XX 件」，点击 worker 开 Modal 明细表）+ 波次完成率环形（中心百分比，四状态配色）+ 作业时效 `boxplot`（入库/出库/盘点 P10–P90）+ 任务进度表（Tab 按类型过滤 + 行内进度条 + 状态标签）。数据源 `generateBiData('efficiency',state)`，**不改后端模型**。验证：四元素渲染、worker 下钻、Tab 过滤正常

## 5. 财务面板并入（Executive 重构）

- [x] 5.1 新建 `BiFinancePanel.vue`：迁移 [ExecutiveView.vue](file:///d:/wms-test/frontend-vue/src/views/ExecutiveView.vue) 的汇总卡 + 账龄环形 + 应收 TOP 条 + 订单/回款趋势折线，图表改用 `BiChart.vue` 承载、外层套 `.bi-scope`；**数据仍调用 `/api/executive/*` 原函数，不改口径**。验证：面板数值与迁移前 Executive、与财务台账一致
- [x] 5.2 从 `useBiState` 的 `activePanel==='finance'` 挂载财务面板；确认 `/bi` 财务面板不受时间/仓库 Mock 筛选器影响（其数据源为真接口）。验证：切到财务面板显示真实驾驶舱内容，其余面板仍 Mock

## 6. 导出与集成回归

- [x] 6.1 面板级导出：各面板「导出」按钮遍历其 `BiChart` 实例 `getDataURL({pixelRatio:2,backgroundColor:'#fff'})` 触发下载，文件名 `WMS-BI-{panel}-{yyyyMMddHHmmss}.png`。验证：点击导出生成清晰 PNG（本 change 不做整页 html2canvas 拼图）
- [x] 6.2 全量回归：`cd frontend-vue; npx vue-tsc --noEmit` 无错误；`npx vitest run` 全绿；`npm run build` 成功；`npm run build:pages`（Mock 模式）成功。验证：四条命令 0 失败
- [x] 6.3 端到端冒烟：`#/bi` 四仓储面板 + 财务面板切换、筛选联动、下钻 Modal、导出、旧 `#/executive` 重定向逐项走通；主站任一业务页样式无回归。验证：手动操作无报错、无样式串扰
- [x] 6.4 更新 `NOTES.md`/`TASKS.md`：登记 BI 工作台落地与「仓储看板 `/dashboard` 收敛、真实 `/api/bi/*` 接入、p0-2 字段复用」三项后续。验证：文档与实际范围一致
