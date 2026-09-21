---
kind: dependency_management
name: 多语言依赖管理：uv + pyproject.toml/requirements.txt 与 npm lockfile
category: dependency_management
scope:
    - '**'
source_files:
    - backend-python/pyproject.toml
    - backend-python/uv.lock
    - backend-python/requirements.txt
    - backend-python/api/requirements.txt
    - frontend-vue/package.json
    - frontend-vue/package-lock.json
    - package.json
---

## 1. 使用的系统与工具

本仓库为前后端同仓（monorepo）项目，Python 后端与 Vue 前端各自使用独立的包管理器，并通过顶层 `package.json` 的脚本统一编排启动。

- **Python 后端**：以 `backend-python/pyproject.toml` 作为声明式依赖清单（`[project.dependencies]`、`[project.optional-dependencies]`），使用 `uv` 作为解析器与锁文件生成器，锁定文件为 `backend-python/uv.lock`；同时保留 `backend-python/requirements.txt` 用于 Render 平台自动识别安装，以及 `backend-python/api/requirements.txt` 用于 Vercel 函数部署。
- **Vue 前端**：以 `frontend-vue/package.json` 声明依赖，使用 `npm` 并生成 `frontend-vue/package-lock.json`（lockfileVersion: 3）。
- **根级编排**：根目录 `package.json` 仅包含 `concurrently` 作为 devDependency，提供 `start:backend`、`start:frontend`、`start` 三个脚本，通过 `cd backend-python && uv run uvicorn ...` 启动后端，实现“一键启动”。

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `backend-python/pyproject.toml` | Python 项目元数据、运行时依赖、可选依赖（dev）、构建系统（setuptools）、pytest 配置 |
| `backend-python/uv.lock` | uv 生成的确定性锁文件，记录每个包的精确版本与 sha256 hash |
| `backend-python/requirements.txt` | Render 部署用依赖清单（与 pyproject 保持同步） |
| `backend-python/api/requirements.txt` | Vercel 函数部署用依赖清单（注释说明必须与后端 requirements 一致） |
| `frontend-vue/package.json` | 前端运行时与开发依赖声明 |
| `frontend-vue/package-lock.json` | npm 锁文件，锁定所有传递依赖的精确版本 |
| `package.json`（根） | 跨模块启动脚本（concurrently） |
| `.github/workflows/ci.yml` | CI 中执行 `uv sync` / `npm ci` 等安装流程（由工作流驱动） |

## 3. 架构与约定

### 3.1 Python 依赖分层

- **运行时依赖**集中在 `pyproject.toml` 的 `dependencies` 字段（fastapi、uvicorn、sqlalchemy、pydantic、aiosqlite、pymysql、psycopg2-binary、alembic、python-dotenv），并通过 `requires-python = ">=3.11"` 约束解释器版本。
- **开发依赖**通过 `[project.optional-dependencies] dev = [...]` 定义（pytest、httpx、pytest-asyncio），不污染生产环境。
- **构建系统**使用 setuptools（`build-system.requires = ["setuptools>=61.0"]`），支持 `pip install .` 在 Docker 镜像或 CI 中安装整个包。
- **双清单策略**：`requirements.txt` 是 `pyproject.toml` 的扁平化副本，专门供 Render 平台读取；`api/requirements.txt` 额外包含 `mangum` 用于 Vercel Serverless 函数。三者需人工保持一致（见 `api/requirements.txt` 顶部注释）。
- **锁文件**：`uv.lock` 记录每个包的来源 registry（`https://pypi.org/simple`）、sdist/wheel 的 URL 与 sha256 hash，确保可重复构建。

### 3.2 前端依赖管理

- 依赖按 `dependencies`（axios、element-plus、echarts、pinia、vue、vue-router、@element-plus/icons-vue）与 `devDependencies`（vite、typescript、vitest、playwright、vue-tsc）严格区分。
- 版本号采用 `^` 语义化版本范围（如 `^3.4.0`、`^2.7.0`），由 `package-lock.json` 锁定实际解析出的精确版本。
- 从 `package-lock.json` 可见部分包通过 `registry.npmmirror.com` 解析（国内镜像），但主声明仍指向 npm 官方源。

### 3.3 根级编排

根 `package.json` 不声明业务依赖，仅通过 `concurrently` 并行启动前后端：`npm start` 等价于同时运行 `uv run uvicorn app.main:app --port 8000` 与 `npm run dev`，形成统一的本地开发入口。

## 4. 约定与约束

- **Python 解释器版本约束**：`pyproject.toml` 要求 `>=3.11`，`uv.lock` 头部也声明 `requires-python = ">=3.11"`，新贡献者需满足该版本。
- **依赖声明唯一来源**：新增 Python 依赖应优先写入 `pyproject.toml`，再同步到两个 `requirements.txt`（Render 与 Vercel），否则部署可能失败。
- **Vercel 函数目录约定**：`api/requirements.txt` 必须与函数代码放在同一目录（`api/`），这是 Vercel Python 函数的强制要求，注释中已明确说明。
- **Docker 构建**：`backend-python/Dockerfile` 使用 `uv sync` 安装依赖（基于 `uv.lock`），保证容器内环境与本地一致。
- **前端锁定**：CI 与部署应使用 `npm ci`（由 `package-lock.json` 保证），而非 `npm install`，以避免非确定性安装。
- **无私有仓库/代理配置**：未发现 `.npmrc`、`.pypirc`、`pip.conf` 或 `uv` 的自定义 index 配置，依赖均直接来自 PyPI 与 npm 官方源（前端部分包经 npm 镜像缓存解析）。
- **无 vendoring**：未使用 `pip install --no-deps` 将第三方库拷贝进仓库，也未使用 pnpm/poetry 等替代工具。
- **可选依赖隔离**：测试/HTTP 客户端等仅在 `dev` 分组中声明，避免打包进生产镜像。

## 5. 风险与建议

- `requirements.txt` 与 `pyproject.toml` 需要人工同步，存在漂移风险；建议通过脚本或 CI 校验两者一致性。
- 前端使用 `^` 范围版本，若希望完全可重复构建，可在发布前将 `package-lock.json` 提交并确保 CI 使用 `npm ci`。
- 未配置私有 PyPI/npm 源，若未来引入内部包需补充认证与镜像配置。