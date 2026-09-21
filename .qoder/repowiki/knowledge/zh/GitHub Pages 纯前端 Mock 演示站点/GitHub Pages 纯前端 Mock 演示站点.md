---
kind: external_dependency
name: GitHub Pages 纯前端 Mock 演示站点
slug: github-pages
category: external_dependency
category_hints:
    - vendor_identity
    - framework_behavior
scope:
    - '**'
source_files:
    - README.md
    - .github/workflows/deploy-pages.yml
---

### 角色与集成点
- 提供无需后端的纯前端 Mock 演示（`yeyege.github.io/psi-fin/`），构建产物放在 `site/app/`，由 `.github/workflows/deploy-pages.yml` 推送 master 后自动构建并发布。
- 构建模式通过 `build:pages`（读取 `.env.pages`，`VITE_USE_MOCK=true`）生成，路由 base 为 `/psi-fin/app/`。

### 关键约束
- 仅托管静态 SPA，Mock API 在浏览器内实现（`src/api/mock/`），不包含真实后端逻辑。
- 与 Vercel/Render 的在线演示不同，此路径完全无后端依赖。