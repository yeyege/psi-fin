---
kind: build_system
name: PSI-FIN 全栈构建与部署体系（Docker Compose / GitHub Actions / Render Blueprint）
category: build_system
scope:
    - '**'
source_files:
    - docker-compose.yml
    - backend-python/Dockerfile
    - frontend-vue/Dockerfile
    - .github/workflows/ci.yml
    - .github/workflows/deploy-pages.yml
    - render.yaml
    - backend-python/pyproject.toml
    - package.json
---

## 1. 构建系统概览

本项目采用**多模块、多语言、容器化**的构建与部署方案：后端使用 Python FastAPI（`backend-python/`），前端使用 Vue 3 SPA（`frontend-vue/`），通过 `docker-compose.yml` 提供本地一键启动，通过 GitHub Actions 执行 CI 检查与测试，通过 Render Blueprint (`render.yaml`) 实现云端一键部署，并通过 `.github/workflows/deploy-pages.yml` 将前端静态站点发布到 GitHub Pages。

## 2. 关键文件与职责

- **`docker-compose.yml`**：定义三服务编排（MySQL 8.0 + FastAPI 后端 + Nginx 托管的前端），通过环境变量注入数据库连接串，使用 `healthcheck` 确保 MySQL 就绪后再拉起后端。
- **`backend-python/Dockerfile`**：基于 `python:3.11-slim`，安装依赖时优先使用清华源并自动 fallback 到腾讯云/阿里源，以 `uvicorn app.main:app` 启动；依赖声明在 `pyproject.toml`（含 `dev` 可选依赖）。
- **`frontend-vue/Dockerfile`**：双阶段构建——`node:20-alpine` 阶段执行 `npm ci`（失败回退 `npm install --legacy-peer-deps`）并 `npm run build`，产物由 `nginx:alpine` 托管，额外设置 `ESBUILD_BINARY_PATH` 修复 overlayfs 下 esbuild postinstall 问题。
- **`.github/workflows/ci.yml`**：三个并行 job：
  - `backend-test`：Python 3.11，`pip install -e ".[dev]"` 后运行 `pytest -q`（不连真实数据库）。
  - `frontend-build`：Node 18，`npm ci` → `npm run build` → `npm test`（Vitest）。
  - `docker-build`：用 `docker/build-push-action@v5` 分别构建前后端镜像（仅 `push: false` 校验）。
- **`.github/workflows/deploy-pages.yml`**：触发条件为 push/PR 到 master 或手动 `workflow_dispatch`，构建 Vue SPA（`npm run build:pages`，base 设为 `/psi-fin/app/`），将 `frontend-vue/dist` 复制到 `site/app/`，通过 `actions/deploy-pages@v4` 发布到 GitHub Pages。
- **`render.yaml`**：Render Blueprint，声明 PostgreSQL 免费实例、Python Web Service（`rootDir: backend-python`，`buildCommand: pip install -r requirements.txt`，`startCommand: uvicorn ...`）、Static Site（`rootDir: frontend-vue`，`publish: dist`），并通过 `fromDatabase.connectionString` 自动注入数据库连接。
- **根 `package.json`**：提供 `start:backend`、`start:frontend`、`start`（`concurrently` 同时启动前后端）脚本，作为本地开发统一入口。

## 3. 架构与约定

- **分层容器化**：后端镜像暴露 8000 端口，前端镜像通过 Nginx 暴露 80 端口，Compose 映射到宿主机 8000/8080。
- **环境配置分离**：数据库凭据通过 Docker 环境变量注入（`MYSQL_ROOT_PASSWORD`、`DATABASE_URL`），Render 通过 `envVars` 注入 `DATABASE_URL` 和 `VITE_API_BASE`。
- **CI/CD 解耦**：CI 只做构建与测试验证，不推送镜像；Pages 部署独立 workflow；生产部署走 Render Blueprint。
- **网络容错**：Dockerfile 中 npm/pip 均配置了备用镜像源与重试参数，提升弱网下的构建稳定性。

## 4. 约定与约束

- 本地开发统一通过 `docker compose up -d --build` 启动三服务（见 `docker-compose.yml` 顶部注释）。
- 后端依赖管理使用 `pyproject.toml`（`pip install .` 用于 Docker/CI），可选依赖通过 `[project.optional-dependencies] dev` 提供。
- 前端依赖锁定使用 `package-lock.json`，CI 强制 `npm ci`，构建失败时 Dockerfile 内回退到 `npm install --legacy-peer-deps`。
- CI 仅在 `master` 分支触发，PR 也会运行相同 job。
- Pages 部署要求 Node 20 且 SPA base 路径为 `/psi-fin/app/`，构建产物必须位于 `site/app/`。
- Render 部署需先完成后端部署，再将 `VITE_API_BASE` 替换为实际后端公网域名（见 `render.yaml` 注释警告）。
- 数据库健康检查：Compose 中 MySQL 通过 `mysqladmin ping` 检测，后端 `depends_on` 条件为 `service_healthy`。
