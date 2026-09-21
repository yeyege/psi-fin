---
kind: frontend_style
name: BI 工作台 Apple 风格主题与 ECharts 图表主题体系
category: frontend_style
scope:
    - '**'
source_files:
    - frontend-vue/src/styles/bi-apple.css
    - frontend-vue/src/views/bi/biChartTheme.ts
    - frontend-vue/src/api/mock/bi.ts
    - frontend-vue/package.json
    - frontend-vue/vite.config.ts
    - frontend-vue/src/views/bi/BiWorkbenchView.vue
---

## 1. 采用的样式系统与方法论

本仓库的前端（`frontend-vue`）采用 **Vue 3 + Element Plus** 作为主 UI 框架，但 BI 工作台区域并未沿用 Element Plus 的默认主题，而是通过一份独立的 CSS 文件 `src/styles/bi-apple.css` 实现了一套 **Apple 风格的局部主题**。该主题遵循以下约定：

- **命名空间隔离**：所有规则以 `.bi-scope` 为根选择器前缀，禁止裸元素选择器，避免污染 Element Plus 主站样式。这是写在 CSS 文件头部注释中的明确约束。
- **CSS 变量驱动设计令牌**：在 `.bi-scope` 下集中声明背景、卡片、文字、品牌色（蓝/绿/橙/红/紫/青）、圆角（`--bi-radius-lg/md/sm`）、模糊（`--bi-blur`）和阴影等设计令牌，供组件复用。
- **BEM 式类名**：使用 `bi-topbar`、`bi-title`、`bi-dock`、`bi-card`、`bi-kpi`、`bi-stat`、`bi-alert`、`bi-todo`、`bi-rank`、`bi-gauge` 等语义化类名组织布局与组件。
- **响应式策略**：基于 CSS Grid + `@media (max-width: 1100px)` 断点，将 4 列网格降级为 2 列或 1 列；Dock 导航支持横向滚动。
- **动效**：面板切换使用 `biFade` 淡入动画，Modal 使用 `biSlideUp` 上滑动画，按钮 hover 有轻微位移过渡。

## 2. 关键文件与包

| 文件 | 作用 |
|---|---|
| `frontend-vue/src/styles/bi-apple.css` | BI 工作台 Apple 主题全部样式（约 250 行），定义设计令牌、布局、KPI 卡、统计卡、预警列表、排行榜、进度表、仪表盘、Modal 等 |
| `frontend-vue/src/views/bi/biChartTheme.ts` | ECharts 统一主题工厂：导出 `BI_PALETTE`、`biOption()` 包装函数、通用坐标轴配置 `axisCategory` / `axisValue`、图表导出工具 |
| `frontend-vue/src/api/mock/bi.ts` | BI Mock 数据层，同时集中维护 `BI_THEME` 颜色常量（与 CSS 变量一一对应），保证图表配色与 CSS 一致 |
| `frontend-vue/package.json` | 依赖声明：`element-plus`、`echarts`、`pinia`、`vue-router`、`axios`，无 Tailwind / Sass / Less |
| `frontend-vue/vite.config.ts` | Vite 构建配置，仅引入 `@vitejs/plugin-vue`，无 CSS 预处理器插件 |
| `frontend-vue/src/views/bi/BiWorkbenchView.vue` | 唯一挂载 `.bi-scope` 根容器的视图入口 |

## 3. 架构与约定

- **主题来源**：CSS 注释写明“设计变量取自原型 `apple-store-wms.html`”，说明样式是直接从静态原型移植到 Vue 工程，保持视觉一致性。
- **双源设计令牌**：颜色令牌同时存在于两处——CSS 变量（`--bi-blue` 等）用于 DOM 样式，JS 常量 `BI_THEME`（`blue`、`green`、`orange`、`red`、`purple`、`cyan`、`grey` 等）用于 ECharts 配色，两者数值完全对齐，避免视觉割裂。
- **图表主题工厂模式**：`biOption(opt)` 接收业务 option 并合并统一的字体（`-apple-system, 'SF Pro Display', 'PingFang SC'`）、配色、tooltip、grid、动画时长等基础样式，再展开业务配置，确保所有图表风格一致。
- **组件级样式隔离**：BI 相关组件（`BiOverviewPanel`、`BiInventoryPanel`、`BiFlowPanel`、`BiEfficiencyPanel`、`BiChart`、`BiModal`、`SummaryCards`）均包裹在 `.bi-scope` 容器中，通过 class 选择器而非全局样式生效。
- **无 CSS 预处理器**：项目未安装 Sass/Less/Tailwind，纯原生 CSS + CSS 变量，由 Vite 直接编译。

## 4. 约定与约束

- **强制命名空间**：`bi-apple.css` 顶部注释明确要求“全部规则以 `.bi-scope` 前缀限定，禁止裸元素选择器，避免污染 Element 主站”——这是样式隔离的硬性约定。
- **设计令牌集中管理**：颜色、圆角、阴影、模糊等视觉变量必须从 `.bi-scope` 下的 CSS 变量读取，不得在组件内硬编码十六进制值。
- **ECharts 主题统一**：所有图表必须通过 `biOption()` 包装，使用 `BI_PALETTE` 调色板，不得使用内置默认配色。
- **字体栈固定**：正文与图表统一使用 `-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif`，禁止覆盖。
- **响应式断点**：Grid 布局在 `1100px` 处降级，新增布局需遵循此断点策略。
- **无全局样式泄漏**：Modal 通过 Teleport 到 body 时仍保持在 `.bi-scope.bi-modal-root` 命名空间下，确保弹窗样式不泄露到主应用。