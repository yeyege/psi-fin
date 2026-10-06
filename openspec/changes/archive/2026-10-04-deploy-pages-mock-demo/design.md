## Context

见 proposal.md - Why。已核实的现状:

- `deploy-pages.yml` 在 push `master` 时**原样上传 `site/` 目录**(已入库 4 个文件:落地页 + 两个静态演示页 + `.nojekyll`)。
- `site/`(入库)与 `preview/`(被 `.gitignore` 忽略)是两份手工副本,**已不同步**:本轮修订只落在 `preview/`。
- `frontend-vue/vite.config.ts` 未配置 `base`;`src/api/client.ts` 的 `baseURL` 硬编码为 `/api`,依赖 Vite dev 代理(生产由 nginx 反向代理)。
- 路由为 `createWebHashHistory`(hash 模式),天然规避静态托管刷新 404。
- 后端 FastAPI + SQLite 无法部署到 GitHub Pages;后端 CORS 已是 `*`(为将来上云跨域调用预留,本变更不使用)。
- 仓库 `yeyege/wms`,默认分支 `master`,站点地址 `https://yeyege.github.io/wms/`(**子路径 `/wms/`**)。

## Goals / Non-Goals

**Goals:**

- 线上站点在**没有后端**的情况下也能完整演示收入侧业财闭环(建单 → 发货 → 应收 → 收款核销 → 驾驶舱)。
- SPA 在 `/wms/app/` 子路径下资源正确、刷新不 404。
- push master 自动构建并发布,构建产物不入库。
- 静态演示页只有一个发布来源,且在线上是最新版。
- 保留"一键切真后端"的能力(上云作为后续变更)。

**Non-Goals:**

- 不在本次部署后端/数据库,不做真实鉴权与数据持久化(演示账号固定)。
- 不把库存/基础数据等旧页面改造成 Mock 完整实现,仅做接口兜底避免崩溃。
- 不做 CDN、缓存策略、多环境(预发/生产)等发布工程化增强。

## Decisions

### 1. 站点结构:根=落地页 + 静态演示页,SPA 放 `/app/`

保留站点根为落地页(项目介绍 + 入口卡片),静态演示页与其同级,SPA 发布到 `/app/`。
理由:原链接 `https://yeyege.github.io/wms/` 目前是精致的演示落地页,若让 SPA 占据根路径,首屏会变成登录页,面试浏览体验明显变差,且会破坏"同一个链接既是门面又是系统"的叙事。
备选(SPA 占根 + 静态页移入 `/preview/`):改动更简单,但牺牲首屏体验,放弃。

### 2. Mock 实现:自定义 axios adapter,零新增依赖

在 `client.ts` 中按开关设置 `api.defaults.adapter = mockAdapter`,adapter 按 `method + path` 正则匹配到本地 handler;命中则返回标准 `AxiosResponse`(`{ data: { code, message, data } }`),未命中走**通用兜底**。
理由:现有响应拦截器是 `res => res.data`,只要 adapter 返回同形状对象即可复用全部页面代码,无需改动任何 view;不引入 `axios-mock-adapter`/MSW 的依赖与体积。
备选:引入 MSW(Service Worker 拦截)——更"真",但增加依赖与构建复杂度,对纯展示不划算。

### 3. 开关与地址:全部走构建期环境变量

- `VITE_USE_MOCK`(默认 `false`)控制 Mock 是否启用;
- `VITE_BASE`(默认 `/`)控制资源基础路径;
- `VITE_API_BASE`(默认 `/api`)控制真实接口地址。
理由:Vite 只把 `VITE_` 前缀变量注入客户端,三者都可在 CI 构建命令里注入,本地零影响;将来上云只需换变量。

### 4. Mock 数据:内存态 + 固定演示数据 + 刷新重置

内置一组客户/商品/订单/应收/部分回款数据;刷新即回到初始状态。
理由:演示可重复、无需任何持久化;规则必须与后端 specs 同口径(发货才生成应收、幂等、部分核销、预收、超额拦截、账龄按到期日),否则会讲出两套账。

### 5. 静态演示页来源:`site/` 为发布源

`site/` 是发布唯一来源;`preview/` 保持被忽略,定位为本地素材目录(截图、给 HR 的文案)。本次把 `preview/` 里最新的两个演示页同步进 `site/`。
理由:消除双份不同步问题,且不需要改动 `.gitignore` 与历史习惯。

### 6. 发布流程:CI 构建 + 组装站点

`deploy-pages.yml` 改为:checkout → setup-node(20)→ `npm ci` → `npm run build:pages`(注入 `VITE_USE_MOCK=true`、`base=/wms/app/`)→ 复制 `frontend-vue/dist` 到 `site/app/` → 上传 `site/` → 部署。`site/app/` 加入 `.gitignore`,构建产物不入库。

## Risks / Trade-offs

- [Mock 规则与后端漂移 → 讲出两套账] → Mock 的关键规则集中在 `mock/` 单一模块实现,并以本变更 specs 的场景作为验收口径;本地用脚本把闭环流程跑一遍。
- [子路径写死 `/wms/app/` → 仓库改名/换路径即失效] → base 值集中在构建脚本与配置,README 说明修改点。
- [兜底空数据被误认为"功能坏了"] → 落地页/README 标注演示范围:业财闭环为 Mock 完整实现,库存等页面为展示壳。
- [CI 增加前端依赖安装,时间变长] → 使用 `actions/setup-node` 的 npm 缓存;单次构建可接受。
- [本地无 `site/app/` 产物时无法完整预览站点] → 提供本地"以子路径预览构建产物"的方式(`vite preview` 或静态服务指定目录),用于发布前校验。

## Migration Plan

- 部署:推送 `master` 后由 Actions 自动构建并发布;站点根与 `/app/` 同时更新。
- 回滚:回退 `deploy-pages.yml` 与相关配置即可恢复"只发静态页"的旧行为。
- 切真后端(后续变更):关闭 `VITE_USE_MOCK`、设置 `VITE_API_BASE` 指向云端后端地址并重新构建,无需改动页面代码。
