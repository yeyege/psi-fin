## Why

GitHub Pages 是纯静态托管,**FastAPI 后端无法部署上去**,所以线上站点不可能直接跑真后端。而当前 Pages 只发布了静态演示页(`site/` 下的方案页与 BI 看板),无法展示"能走通的业财闭环";同时存在两个具体缺陷:Vite 未配置 `base`,部署到 `/wms/` 子路径会资源 404;`site/`(已入库)与 `preview/`(被 gitignore)是两份手工副本,**已经不同步**(最新改动只在 preview)。本变更让线上站点变成"**前端可用 + Mock 数据驱动**"的业财一体演示:无需后端即可走通 建单 → 发货 → 应收 → 收款核销 → 驾驶舱;真后端上云作为后续变更,本次预留切换能力。

## What Changes

- 新增**前端 Mock API 模式**:通过构建开关启用后,所有 `/api` 请求由浏览器内本地实现响应(不发起真实网络请求),覆盖 登录、客户/商品、销售订单(建单/确认/发货/完成/作废)、财务(应收列表/账龄/收款核销)、经营驾驶舱(汇总/排行/账龄分布/趋势);并**复刻后端关键规则**(发货才生成应收且幂等、部分核销与结清、单张超额拦截、预收余额、账龄按到期日分段、驾驶舱与财务同口径)。
- **未覆盖接口兜底**:其余 `/api` 请求返回空分页/空对象,保证旧页面不因缺接口而崩溃。
- **前端支持子路径部署**:Vite `base` 可配置;API `baseURL` 可配置(`VITE_API_BASE`,默认 `/api`),为将来切真后端预留。
- **Pages 站点结构调整**:站点根保留落地页与静态演示页;新增 `/wms/app/` 子路径发布 Vue SPA;落地页新增"在线系统"入口。
- **发布流程改造**:`deploy-pages.yml` 从"直接上传 site/"改为"**构建前端 → 组装站点(拷贝 dist 到 site/app)→ 发布**";构建时注入 mock 开关与 base;构建产物不入库。
- **静态演示页来源统一**:以 `site/` 为唯一发布源,本次把 `preview/` 里最新的方案页同步进 `site/`。
- **不改后端**:`backend-python/` 不动,本地开发仍连真实后端;上云作为后续变更。

## Capabilities

### New Capabilities
- `deployment/mock-api`: 纯前端 Mock 模式 — 开关控制、覆盖业财核心接口、复刻后端业务规则、内置演示数据、未覆盖接口兜底,使无后端环境也能完整演示收入侧业财闭环。
- `deployment/pages-static-site`: GitHub Pages 静态站点 — 站点目录结构(落地页 + 静态演示页 + `/app/` 子路径 SPA)、子路径资源正确性、push 自动构建发布流程、静态演示页单一来源一致性。

### Modified Capabilities
(无。现有 WMS 与业财功能的行为规范不变。)

## Impact

- **前端**:新增 `frontend-vue/src/api/mock/`(数据 + 适配器);修改 `src/api/client.ts`(mock 开关 + API base 可配置)、`vite.config.ts`(`base` 可配置);新增 `build:pages` 脚本。
- **CI/发布**:修改 `.github/workflows/deploy-pages.yml`(增加 Node 构建与站点组装步骤);`.gitignore` 增加 `site/app/` 构建产物。
- **站点**:`site/index.html` 增加"在线系统"入口;`site/business-console-plan.html`、`site/apple-store-wms.html` 同步为最新版本。
- **不涉及**:`backend-python/`、数据库、既有 15 个库存/基础数据页面行为。
- **无新增第三方依赖**:Mock 通过自定义 axios adapter 实现(不引入 axios-mock-adapter / MSW)。
- **兼容性**:本地开发默认不启用 mock(`/api` 仍走 Vite 代理到 8000),行为与现在一致;启用仅由构建开关/环境变量触发。
