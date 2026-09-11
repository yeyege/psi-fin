## Why

求职场景需要向招聘方(电商行业、以低代码平台搭建"业财一体 + 公司中后台"的公司)直观展示"从业务梳理到系统落地"的完整能力。此前已直接产出了单文件演示页 `preview/business-console-plan.html`,但它没有规范记录:方案的内容口径、模块划分、验收标准、以及后续迭代方向(迁移到 `frontend-vue` 或复用到真实低代码搭建)都无法被追踪和复用。本 change 将该演示资产固化为 spec 化变更,沉淀"业财一体中后台方案"的结构与口径,支撑面试讲解与后续落地。

## What Changes

- 把已产出的单文件演示页 `preview/business-console-plan.html`(纯静态、零依赖、浏览器直接打开)固化为正式交付资产,并新增 specs 定义其内容结构与交互行为(新增能力,无存量行为改动)。
- 固化"菜单蓝图"的域划分与模块粒度:经营驾驶舱 / 销售 / 采购 / 库存 / 生产代工 / 财务 / 行政人事 / 系统管理 8 大域,作为未来落地低代码平台或迁移 Vue 的参考基线。
- 明确演示页各区块(整体架构、菜单蓝图、业财链路、数据接入、实施路线、BI 看板内嵌、能力对照)的存在与一致性要求。
- 无代码行为变更(演示页为静态示意数据,不承接真实业务)。

## Capabilities

### New Capabilities
- `demo/business-console`: 定义 `preview/business-console-plan.html` 作为"业财一体中后台搭建方案演示页"必须具备的内容结构、交互行为与口径一致性约束,包括导航、菜单蓝图 Mock、业财链路、数据管线、路线图、BI 内嵌与能力对照。

### Modified Capabilities
(无)

## Impact

- **涉及文件**:规划产物位于本 change 目录;实现文件为已有的 `preview/business-console-plan.html`,被引用资产为 `preview/apple-store-wms.html`。不改动 `frontend-vue/` 与 `backend-python/`。
- **无新增依赖 / 无构建链 / 无运行时要求**:演示页保持单文件可打开;页面文案为面试演示用示意结构,不接真实数据。
- **后续可复用**:本方案模块划分与链路口径可作为未来简道云搭建或 `frontend-vue` 迁移(如 Apple Store 风格重构)的需求基线。
