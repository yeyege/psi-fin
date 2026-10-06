## Purpose

定义 Vue 应用内的全幅 BI 工作台外壳能力：一条 `/bi` 路由承载 Apple 风格局部主题、分段 Dock 面板切换、全局时间/仓库筛选联动、下钻 Modal、图表级导出，并将既有财务驾驶舱作为「经营财务」面板并入，形成统一「看数」入口。

## ADDED Requirements

### Requirement: 全幅 BI 工作台路由
系统 SHALL 在前端提供一级路由 `/bi`，渲染全幅 BI 工作台 `BiWorkbenchView`，工作台内部自带顶栏与分段 Dock 布局，与主站 Element 布局互不侵入。

#### Scenario: 从侧边栏进入工作台
- **WHEN** 用户点击侧边栏「经营驾驶舱」组的 BI 工作台入口
- **THEN** 路由跳转到 `/bi` 并渲染工作台，默认显示「数据总览」面板，主站侧边栏/顶栏样式不变

#### Scenario: 旧驾驶舱路由重定向
- **WHEN** 用户访问历史地址 `#/executive`
- **THEN** 系统 SHALL 自动重定向到 `/bi`，不出现 404 或空白页

### Requirement: Apple 局部主题作用域隔离
工作台 SHALL 通过 `.bi-scope` 作用域类引入 Apple 风格设计变量（蓝/绿/橙/红/紫、大圆角、毛玻璃等），所有相关样式规则必须以 `.bi-scope` 前缀限定，不得定义裸元素选择器污染全局。

#### Scenario: 主题仅在工作台生效
- **WHEN** 用户离开 `/bi` 进入任一业务页（如库存、销售订单、用户管理）
- **THEN** 业务页外观 SHALL 与引入本 change 前完全一致，无 Apple 变量串扰

### Requirement: 分段 Dock 面板切换
工作台 SHALL 提供分段 Dock，含「数据总览 / 库存分析 / 出入库分析 / 作业效率 / 经营财务」五个面板项，点击切换主内容区显示对应面板，同一时刻仅一个面板可见。

#### Scenario: 面板切换保留筛选态
- **WHEN** 用户已设置时间/仓库筛选后在 Dock 间切换面板
- **THEN** 激活项高亮，主内容区以淡入动画切换到目标面板，且当前筛选状态 SHALL 保持不变

### Requirement: 全局筛选联动刷新
工作台顶栏 SHALL 提供统一时间范围筛选器（今日 / 近 7 天 / 近 30 天 / 自定义起止，起止需满足结束≥开始且不超过今日）与仓库多选筛选器（含「全部仓库」）。任一筛选变更时，所有 Mock 仓储面板 SHALL 依据新状态重新生成数据并刷新图表，期间显示 loading 遮罩而不销毁重建图表。

#### Scenario: 筛选变更联动
- **WHEN** 用户修改时间范围或勾选/取消仓库
- **THEN** 当前 Mock 面板的 KPI 与图表在 500ms 内按新条件刷新，无白屏闪烁

#### Scenario: 非法自定义日期被拦截
- **WHEN** 用户选择自定义日期且结束日期早于开始日期或晚于今日
- **THEN** 系统 SHALL 以红色提示标记非法，不触发数据刷新

### Requirement: 下钻详情弹窗
工作台 SHALL 提供通用 Modal 组件用于下钻（如库存预警条目、作业员明细），支持点击遮罩、右上角关闭按钮、ESC 键三种关闭方式。

#### Scenario: 打开与关闭 Modal
- **WHEN** 用户触发下钻事件
- **THEN** Modal 从底部滑入居中、背景半透明模糊；三种关闭方式均有效

### Requirement: 图表级 PNG 导出
工作台 SHALL 在顶栏提供「导出」按钮，对当前面板内每个图表以其 ECharts 实例 `getDataURL`（pixelRatio=2、白底）生成 PNG 并触发下载，文件名格式 `WMS-BI-{面板名}-{yyyyMMddHHmmss}.png`。

#### Scenario: 导出当前面板图表
- **WHEN** 用户点击「导出」
- **THEN** 当前面板各图表生成高清 PNG 下载；不依赖 html2canvas 等新增外部依赖

### Requirement: 统一图表容器契约
工作台所有图表 SHALL 通过统一容器组件 `BiChart.vue` 渲染 ECharts；该组件负责实例初始化、`setOption` 更新、尺寸自适应（容器/窗口 resize）、卸载时 `dispose`，并对外暴露导出图片与获取实例能力，且默认注入一致的 Apple 调色。

#### Scenario: 图表随容器自适应与回收
- **WHEN** 面板图表所在容器尺寸变化或面板被卸载
- **THEN** `BiChart` SHALL 自动 resize 保持清晰，卸载时释放 ECharts 实例，不产生泄漏

### Requirement: 经营财务面板并入且口径不回退
工作台 SHALL 提供「经营财务」面板，复用现有 `/api/executive/*` 数据与计算（应收汇总、账龄分布、应收 TOP、订单/回款趋势），呈现宿主由独立 `/executive` 页改为工作台内面板，其数据口径 SHALL 与 `finance/executive-dashboard` 既有要求保持一致。

#### Scenario: 财务面板数据与迁移前一致
- **WHEN** 用户切换到「经营财务」面板
- **THEN** 面板展示的金额类指标 SHALL 与迁移前的 Executive 页及财务台账一致，不因并入而改变计算

#### Scenario: 财务面板不受 Mock 筛选器影响
- **WHEN** 用户修改时间/仓库 Mock 筛选器后停留在财务面板
- **THEN** 财务面板数据源为真接口，SHALL 不因仓储 Mock 筛选器而改变其口径（该面板按自身数据逻辑展示）
