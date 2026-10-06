## Purpose

定义 BI 工作台的 Mock 数据层能力：以可复现的 seeded 伪随机纯函数为四个仓储分析面板供数，前端直接 import、不发起任何网络请求，保证演示在无真实数据条件下稳定可交互，并为后续接入真实聚合接口预留同构的返回结构。

## ADDED Requirements

### Requirement: seeded 可复现伪随机
Mock 数据层 SHALL 使用可复现的伪随机实现（`mulberry32(seed)` + `hashString(str)`），种子由当前筛选状态派生：`seed = hash(timeRange 预设 + 起止日期 + 排序后的仓库集合)`。相同筛选状态下多次生成 SHALL 得到完全一致的数据，不同筛选状态 SHALL 产生合理差异。

#### Scenario: 同条件数据稳定
- **WHEN** 在相同时间范围与仓库集合下连续两次请求同一面板数据
- **THEN** 两次返回的数据结构逐字段相等，面板不因重复渲染而数值横跳

#### Scenario: 换筛选条件数据变化
- **WHEN** 用户切换时间范围或仓库集合
- **THEN** 生成结果 SHALL 随种子变化而改变，但仍落在各指标既定合理区间内

### Requirement: 分视图纯函数生成器
Mock 数据层 SHALL 以 `generateBiData(view, state)` 为唯一入口，按视图分派到 `mockOverview / mockInventoryAnalysis / mockFlowAnalysis / mockEfficiency` 纯函数，各函数返回强类型结构（沿用原型 camelCase 字段命名），且各视图字段与合理范围 SHALL 与 `bi-dashboard-apple-style` 原型一致（如库容使用率 50~95%、退货率 1%~8%、人均拣货 50~200 件/天、ABC 金额约 70%/20%/10%）。

#### Scenario: 面板按需取数
- **WHEN** 某面板以当前筛选状态请求数据
- **THEN** `generateBiData` 返回该视图对应结构且字段齐全，面板无需二次加工即可渲染

### Requirement: 纯前端直连、不走网络适配
BI 仓储面板数据 SHALL 通过直接 import 的纯函数获得，MUST NOT 注册进 axios `mockAdapter` 的 REST 路径表、MUST NOT 发起任何 HTTP 请求；财务面板不在本数据层范围内（沿用 `/api/executive/*`）。

#### Scenario: 断网仍可演示
- **WHEN** 在无后端服务运行（或纯前端 Pages 部署）下打开仓储面板
- **THEN** 数据 SHALL 正常生成渲染，浏览器网络面板无 `/api/bi/*` 请求

### Requirement: 可复现性回归锁定
Mock 数据层 SHALL 附带单元测试，断言：同一 `state` 两次 `generateBiData` 深度相等；不同 `timeRange` 或仓库集合产生不同数据；各视图返回结构字段齐全。

#### Scenario: CI 保障数据层契约
- **WHEN** 运行前端单测
- **THEN** `bi.ts` 可复现性与结构契约用例 SHALL 全部通过，作为该层的回归护栏
