## Purpose

定义 BI 工作台「库存分析」面板能力（Mock 数据、ECharts 渲染）：从 SKU、库龄、批次状态、ABC 分类四个维度分析库存结构，辅助优化周转与资金占用。

## ADDED Requirements

### Requirement: SKU 高/低库存 TOP10
面板 SHALL 并排展示两张 ECharts 水平柱状图：库存数量最高 10 个 SKU（含数量与占总量百分比）与低于阈值的最低库存 10 个 SKU（红/橙警示色）。仓库筛选变更时 SHALL 重算排名。

#### Scenario: TOP10 渲染
- **WHEN** 用户切换到「库存分析」面板
- **THEN** 左图高库存 TOP10、右图低库存 TOP10 并排渲染

#### Scenario: 仓库过滤重算
- **WHEN** 用户修改仓库筛选
- **THEN** 两张 TOP10 图按所选仓库集合重算排名

### Requirement: 库龄分布饼图
面板 SHALL 以饼图展示库龄分布（<30 天 / 30–90 / 90–180 / 180–365 / >365 共 5 段），hover 显示区间名称、SKU 数量、占比与估算滞压金额。

#### Scenario: 库龄分析展示
- **WHEN** 进入库存分析面板
- **THEN** 饼图 5 个扇区，hover 显示四项明细

### Requirement: 批次状态分布堆叠柱
面板 SHALL 以按仓库分组的堆叠柱展示批次状态（正常 / 临期 / 已过期 / 冻结）数量分布，X 轴为仓库、Y 轴为批次数、每仓库堆叠 4 种状态。

#### Scenario: 批次堆叠渲染
- **WHEN** 进入库存分析面板
- **THEN** 各仓库按 4 种批次状态堆叠展示

### Requirement: ABC 分类帕累托图
面板 SHALL 以双 Y 轴（ECharts bar + line）展示 ABC 帕累托：柱为各 SKU 金额降序、线为累计金额占比，在 70%/90%/100% 处以虚线标注 A/B/C 区间。hover 显示 SKU 名称、金额、所属分类与累计占比。

#### Scenario: 帕累托交互
- **WHEN** 鼠标悬停任一 SKU 柱
- **THEN** tooltip 显示名称、金额、A/B/C 分类、累计占比

### Requirement: 真实数据演进契约（占位）
库存分析面板的库龄/批次状态维度 SHALL 采用与未来真实数据同构的字段口径（库龄天数、批次状态枚举），以便后续接入 `p0-2-strict-fifo-expiry` 将新增的 `ageDays / batchStatus` 时仅替换数据源、不改渲染层；两 change 解耦并行，本面板现阶段以 Mock 供数不阻塞。

#### Scenario: 数据源可替换
- **WHEN** 后续以真实批次效期接口替换 Mock
- **THEN** 渲染层字段与状态枚举 SHALL 保持不变，仅数据源由 `generateBiData` 切换为接口返回
