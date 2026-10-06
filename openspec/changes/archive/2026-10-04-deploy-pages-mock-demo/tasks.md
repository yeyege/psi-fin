> 推进方式:按组顺序实现,每组完成后先跑该组"验证"再进入下一组。
> 状态:全部完成。验证记录见每组条目末尾。

## 1. 前端可配置化(base / API 地址 / 开关)

- [x] 1.1 `vite.config.ts` 支持 `base` 由 `VITE_BASE` 注入(默认 `/`);`src/api/client.ts` 的 `baseURL` 改为 `import.meta.env.VITE_API_BASE || '/api'`。验证:默认 `npm run build` 后 `dist/index.html` 中 `/wms/app` 出现 0 次(base 仍为 `/`),dev 仍走 `/api` 代理
- [x] 1.2 `package.json` 新增脚本 `build:pages`(`vite build --mode pages`,读取 `.env.pages`)。验证:`npm run build:pages` 构建通过,`dist/index.html` 中 `/wms/app/assets` 出现 2 次(资源路径正确)

## 2. Mock 层实现

- [x] 2.1 新增 `src/api/mock/data.ts`:内存演示数据(3 客户 / 6 商品 / 7 订单 / 5 应收 / 2 笔回款)+ 业务规则(发货才生成应收且幂等、部分核销与结清、预收余额复用、超额拦截、账龄按到期日)+ 状态单例与重置。验证:被 `mock.test.ts` 覆盖,刷新/重置后数据回到初始态
- [x] 2.2 新增 `src/api/mock/index.ts`:自定义 axios adapter,覆盖 登录/客户/商品、销售订单(创建/编辑/确认/发货/完成/作废)、应收列表、往来账龄、收款登记与再核销、驾驶舱(汇总/排行/账龄分布/趋势);未覆盖接口返回空分页/空数组/空对象兜底。验证:`mock.test.ts` 8 条用例全过;本地子路径校验中三页面均正常取数
- [x] 2.3 在 `client.ts` 中按 `VITE_USE_MOCK==='true'` 挂载 adapter。验证:Pages 子路径校验中「真实 /api 请求数 = 0」(确认未发真实网络请求);默认模式 e2e(走真实后端)3 用例通过

## 3. 本地验证 Mock 全流程

- [x] 3.1 以 Mock 模式构建并本地预览,验证业财闭环链路。验证:自动化规则用例覆盖 建单→确认→发货→应收(金额/到期日正确)→部分核销→结清→预收再用;UI 层在 Pages 子路径校验中三个页面(销售订单/财务应收/经营驾驶舱)均正常渲染取数
- [x] 3.2 验证关键规则场景:未发货时无该订单应收、重复发货被拒、对未结余额超额核销被拒。验证:`mock.test.ts` 对应用例通过

## 4. 站点结构与静态页同步

- [x] 4.1 `site/index.html` 更新:新增「在线系统(纯前端 Mock 演示)」入口卡片指向 `app/`,标题/副标题改为「进销存 + 业财一体中后台」,并补 favicon。验证:子路径校验中落地页含「在线系统」且 0 资源 404
- [x] 4.2 把 `preview/` 最新 `business-console-plan.html` 与 `apple-store-wms.html` 同步进 `site/`。验证:`site/` 内两页为最新版本(git status 显示已更新)

## 5. 发布流程与文档

- [x] 5.1 改造 `deploy-pages.yml`:checkout → setup-node(20, npm 缓存)→ `npm ci` → `npm run build:pages` → 组装 `site/app/` → 上传 `site/` → 部署。验证:本地按同样步骤模拟组装成功(临时站点 `wms/` 下含落地页 + app/ 30 个文件),子路径访问正常
- [x] 5.2 `.gitignore` 增加 `site/app/`。验证:`git status` 中不出现 `site/app/` 待提交项
- [x] 5.3 `README.md` 增加「在线演示与部署(GitHub Pages)」章节(站点结构表、构建/发布/本地校验/Mock 说明/切真后端方式),并把前端用例数更新为 22。验证:README 章节已落盘

## 6. 回归与发布前校验

- [x] 6.1 默认模式回归:`npm run build`(vue-tsc + vite)通过;`npm run test` **22 passed**(14 原有 + 8 新增 mock 规则);`npm run test:e2e`(真实后端)**3 passed**。验证:与改动前基线一致
- [x] 6.2 发布前本地模拟:按子路径组装站点(`/wms/` = 落地页 + 静态页,`/wms/app/` = SPA)→ 本地静态服务 → Playwright 校验:落地页 OK、SPA 加载 OK、三个业财页面 OK、真实 `/api` 请求 0、`>=400` 响应 0、控制台错误 0。验证:全部通过
