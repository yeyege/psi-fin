## Purpose

把系统以纯静态方式发布到 GitHub Pages(`https://yeyege.github.io/wms/`):站点根保留项目落地页与静态演示页,前端 SPA 发布到 `/app/` 子路径并可通过落地页进入,同时保证子路径下资源加载正确、push 后自动构建发布、静态演示页只有一个来源。

## ADDED Requirements

### Requirement: 站点目录结构

Pages 站点 SHALL 采用如下结构:站点根为落地页 `index.html`(项目介绍 + 入口卡片);静态演示页与其同级(方案页、BI 看板页);Vue SPA 发布在子路径 `/app/` 下。落地页 SHALL 提供进入在线系统(`/app/`)与静态演示页的入口。

#### Scenario: 从落地页进入在线系统

- **WHEN** 打开站点根并点击"在线系统"入口
- **THEN** 跳转到 `/app/` 并成功加载 Vue 应用(登录页或主界面)

### Requirement: 子路径资源正确

SPA 构建 MUST 以部署子路径作为资源基础路径,保证在 `/wms/app/` 下打开时 JS/CSS 等静态资源不出现 404;路由 MUST 使用 hash 模式以规避静态托管的刷新 404 问题。

#### Scenario: 子路径打开无 404

- **WHEN** 在部署环境下访问 `https://yeyege.github.io/wms/app/`
- **THEN** 页面正常渲染,控制台无资源 404 错误

#### Scenario: 刷新不 404

- **WHEN** 在 `/app/` 内切换到任意业务页面(如经营驾驶舱)后刷新浏览器
- **THEN** 页面仍能正常加载

### Requirement: 自动构建与发布

仓库 SHALL 在推送 `master` 时自动完成:安装前端依赖 → 以 Mock 模式与正确 base 构建前端 → 组装站点(构建产物放入 `site/app/`)→ 发布到 GitHub Pages。构建产物 MUST NOT 入库(`site/app/` 被忽略)。

#### Scenario: push 触发发布

- **WHEN** 向 `master` 推送提交
- **THEN** Actions 完成构建与发布,站点根与 `/app/` 均可访问

#### Scenario: 构建产物不入库

- **WHEN** 本地执行前端构建
- **THEN** `site/app/` 处于被忽略状态,不产生待提交变更

### Requirement: 静态演示页来源一致

`site/` SHALL 作为静态演示页的唯一发布来源;`site/` 内的方案页与 BI 看板页 MUST 与最新版本一致(不得落后于本地草稿)。本地保留的草稿目录不参与发布。

#### Scenario: 站点内页面为最新

- **WHEN** 查看已发布的方案页
- **THEN** 其内容与最新修订一致(如菜单域角色、口径表述已更新)

### Requirement: 本地可复现验证

仓库 SHALL 提供可复现的本地验证方式:构建产物可在与部署相同的子路径下被本地服务预览,用于在推送前确认资源路径与页面可用。

#### Scenario: 本地预览子路径

- **WHEN** 开发者按仓库说明在本地以子路径方式预览构建产物
- **THEN** 页面加载正常,可作为发布前校验
