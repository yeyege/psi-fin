## 1. 基础骨架与全局依赖

- [x] 1.1 在 `<head>` 中引入 Chart.js 4.x 与 html2canvas CDN，添加 onerror 降级标记变量（`window.CDN_READY = { chartjs:false, html2canvas:false }`）；3 秒后未就绪则设置降级。验证：浏览器控制台打印 CDN 状态、断网环境下图表区不抛 JS 异常
- [x] 1.2 提取 CSS 色板常量与 JS 常量映射：新增 `const THEME_COLORS = { blue, green, orange, red, purple, blueLight }` 与 `const WAREHOUSES = [{id,name}, ...]`，并在 `<head>` `<style>` 末尾追加全局筛选器、Modal、Page 切换、Loading 遮罩等新组件样式。验证：打开页面筛选器区域 UI 正确渲染，Modal 默认 display:none
- [x] 1.3 实现全局状态对象 `window.BI_STATE = { timeRange:{preset,start,end}, warehouses:['all'], activePage:'overview', charts:new Map() }` 与筛选器 DOM（时间 4 按钮组 + 自定义日期输入框、仓库多选下拉 chip 模式）。验证：点击筛选按钮后 BI_STATE 值正确更新，仓库下拉可多选并回显 chip

## 2. Mock 数据层（seeded PRNG + 四大视图生成器）

- [x] 2.1 实现 `mulberry32(seed)` seeded 伪随机函数与 `hashString(str)` 工具，实现 `generateMockData(state)` 总入口，按 state 计算 seed。验证：相同参数两次调用返回相同数据结构，不同参数返回不同数据
- [x] 2.2 实现 `mockOverview(state)` 返回：kpis[4]、statCards[4]、trendData[{date,inbound,outbound}]、orderStatus[{name,value,color}]、warehouseInventory[{name,available,locked}]、stockAlerts[{level,title,sku,warehouse,current,threshold,daysLeft}]、todos[{tag,tagColor,title,desc,time}]。验证：console.dir 检查数据字段齐全，数值范围合理（库容使用率 50~95% 等）
- [x] 2.3 实现 `mockInventoryAnalysis(state)` 返回：skuTop10[{sku,name,qty,pct}]、lowStockTop10[{sku,name,qty}]、ageDistribution[{range,skuCount,amount}]、batchStatus[{warehouse,normal,nearExpire,expired,frozen}]、abcPareto[{sku,amount,category,cumulativePct}]。验证：A/B/C 三类数量比例约 20%/30%/50%，金额占比约 70%/20%/10%
- [x] 2.4 实现 `mockFlowAnalysis(state)` 返回：trend30[{date,inQty,outQty,inAmt,outAmt}]、netChange、vendorTop10[{vendor,amount,orderCount,onTimeRate}]、customerTop10[{customer,amount,orderCount,returnRate}]、returnTrend[{date,rate}]、returnReasons[{reason,count}]。验证：退货率范围 1%~8%，净增减 = 入库 - 出库
- [x] 2.5 实现 `mockEfficiency(state)` 返回：workerDaily[{worker,days:[{date,qty}]}]、waveStatus[{name,value}]、taskDuration[{type,p10,p25,p50,p75,p90}]、taskList[{taskNo,type,worker,startTime,progress,status}]。验证：人效范围 50~200 件/天，进度 0~100% 随机分布

## 3. 通用交互：页面切换 + Modal + Loading + 导出

- [x] 3.1 实现页面 DOM 结构：在 `<main>` 内创建 `<section class="page page-overview active">` 等 4 个 section，默认仅 overview 可见；实现 `switchPage(pageName)`：修改侧边栏/Dock active 类、用 fade 动画切换 section 显示、首次进入该页面调用对应 render 函数。验证：点击侧边栏 4 个菜单项与底部 Dock 对应图标，页面正确切换，激活态联动
- [x] 3.2 实现全局 Modal：HTML 结构 + `openModal(title, bodyHtml)` + `closeModal()`，支持遮罩点击关闭、ESC 键关闭、从底部滑入动画。验证：打开 Modal 后 3 种关闭方式均有效，遮罩模糊生效
- [x] 3.3 实现筛选联动机制：`function applyFilters()` 遍历 `BI_STATE.charts` 所有 Chart 实例，调用对应 mock 生成新数据 → `chart.data = newData` → `chart.update('none')`；期间在图表容器显示 CSS loading overlay（不销毁重建）。验证：切换筛选后图表 300ms 内更新，无白屏闪烁
- [x] 3.4 实现导出功能：给「导出」按钮绑定点击事件，调用 `html2canvas(document.querySelector('.page.active .export-area') || document.querySelector('main'), {scale:2})` 转 canvas → toDataURL → `<a download>` 触发下载，文件名 `WMS-BI-{pageName}-{yyyyMMddHHmmss}.png`。验证：点击导出后浏览器下载 PNG 图片，分辨率清晰，内容与当前视图一致

## 4. 数据看板 Overview 视图图表渲染

- [x] 4.1 KPI 卡片与统计彩色卡：保留现有 HTML 结构但由 JS 动态注入数值，实现 `renderKpis(data)` 含 trend badge 颜色、进度条宽度动画；实现 `renderStatCards(data)` 点击绑定 switchPage('flow-analysis', {type})。验证：数值与筛选联动，hover 效果保留
- [x] 4.2 出入库趋势柱状图：用 Chart.js bar chart 替换原 CSS 柱状图，dataset1 入库（蓝渐变）/ dataset2 出库（绿渐变），自定义 tooltip 含环比。验证：hover 显示 tooltip，图例点击可隐藏任一数据集
- [x] 4.3 单据状态环形图：用 Chart.js doughnut，中间文字插件显示总数，右侧 JS 渲染图例（数值+百分比）。验证：图例点击切换扇区显隐
- [x] 4.4 仓库库存堆叠水平条：用 Chart.js horizontal bar 堆叠，蓝色可用 + 橙色锁定，右侧标签显示总数。验证：按总库存降序排列
- [x] 4.5 库存预警列表：动态渲染 `<div class="alert-item">`，点击绑定 `openModal('SKU明细', renderSkuDetail(skuData))`，Modal 内显示 5 仓库分布表 + 7 天迷你趋势 sparkline。验证：点击预警条目正确打开 Modal，数据匹配
- [x] 4.6 待办事项网格：JS 动态生成 todo-card 数量（5~8 张），标签色与文案按 mock 数据。验证：hover 上浮效果正常

## 5. 库存分析 / 出入库分析 / 作业效率 三视图实现

- [x] 5.1 库存分析页面板（page-inventory-analysis）DOM 骨架 + 4 个 Chart 实例：SKU TOP10 水平条（左高/右低双图并排）、库龄分布 pie、批次状态堆叠 bar（X 轴仓库）、ABC Pareto（bar + line 双 Y 轴）。验证：进入页面 4 个图表入场动画，数据与 mock 对应
- [x] 5.2 出入库分析页面板（page-flow-analysis）DOM 骨架 + 5 个 Chart/组件：30天趋势双折线（数量/金额切换）、净增减仪表盘（纯 CSS+数字）、供应商 TOP10 条 + 准时率、客户 TOP10 条 + 退货率、退货率折线 + 原因环形图 + 总体退货率>5%红色警示条。验证：指标切换按钮切换折线 Y 轴
- [x] 5.3 作业效率页面板（page-efficiency）DOM 骨架 + 4 项：作业员 7 天分组柱状图（每 worker 堆叠 7 色柱 + 点击 worker → Modal 打开任务明细表）、波次完成率环形（中心百分比）、作业时效箱线图（3 类任务）、任务进度表（Tab 切换类型 + 行内进度条）。验证：点击作业员柱弹出 Modal 含明细表

## 6. 集成验证与回归

- [x] 6.1 全流程手动验证：打开 `preview/apple-store-wms.html` 无 console error → 4 个筛选组合验证（今日/近7天+全仓/仅上海）→ 切换 4 个视图各图表刷新 → 点击 3 处下钻（预警/彩色卡/人效） Modal 正常 → 导出 PNG 功能。验证：全部通过无异常
- [x] 6.2 CDN 降级验证：浏览器 offline 模式打开页面 → 图表区显示降级静态 CSS 占位与文字提示、导出按钮隐藏。验证：无 JS 报错，布局不塌陷
