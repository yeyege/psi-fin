---
kind: configuration_system
name: PSI-FIN 全栈配置体系：环境变量分层与多环境注入
category: configuration_system
scope:
    - '**'
source_files:
    - .env.example
    - docker-compose.yml
    - backend-python/app/database.py
    - backend-python/pyproject.toml
    - frontend-vue/vite.config.ts
    - frontend-vue/.env.pages
    - frontend-vue/src/api/client.ts
    - frontend-vue/package.json
---

## 1. 总体方案

本项目采用**基于 `.env` + Docker Compose + Vite `loadEnv` 的多层环境变量配置体系**，覆盖后端（Python/FastAPI）、前端（Vue/Vite）以及容器编排三个层面。没有引入集中式配置中心或 YAML/JSON 配置文件，所有运行时参数通过环境变量注入。

- **后端**：使用 `python-dotenv`（依赖声明于 `pyproject.toml`），但实际通过 `os.getenv()` 直接读取；数据库连接串由 `DATABASE_URL` 控制，默认回退到 SQLite。
- **前端**：Vite 通过 `loadEnv(mode, process.cwd(), '')` 加载 `.env[.mode]` 文件，仅暴露带 `VITE_` 前缀的变量给浏览器构建产物。
- **容器编排**：`docker-compose.yml` 将根目录 `.env` 中的 MySQL 凭据注入后端容器的 `DATABASE_URL`。
- **演示模式**：通过 `--mode pages` 配合 `.env.pages` 启用纯前端 Mock 模式，无需后端即可运行 GitHub Pages 静态站点。

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `.env.example` | 根级环境变量模板，定义 MySQL 四件套及 `DATABASE_URL` 注释示例 |
| `docker-compose.yml` | 编排 MySQL / backend / frontend 三服务，把 `.env` 变量注入 `DATABASE_URL` |
| `backend-python/app/database.py` | 读取 `DATABASE_URL`，未设置时回退到项目根 `psi_fin.db`（SQLite） |
| `backend-python/pyproject.toml` | 声明 `python-dotenv>=1.0.0` 依赖，定义 dev/test 可选依赖 |
| `frontend-vue/vite.config.ts` | 用 `loadEnv` 读取 `VITE_BASE`、`VITE_API_BASE` 等，配置代理与别名 |
| `frontend-vue/.env.pages` | GitHub Pages 专用模式：`VITE_USE_MOCK=true` + `VITE_BASE=/psi-fin/app/` |
| `frontend-vue/src/api/client.ts` | 根据 `import.meta.env.VITE_API_BASE` 决定 API 基地址，按 `VITE_USE_MOCK` 切换 axios adapter |
| `frontend-vue/package.json` | 提供 `dev` / `build:pages` / `test:e2e` 等脚本，区分不同构建模式 |
| `openspec/config.yaml` | OpenSpec 工具配置（`schema: spec-driven`），与业务配置无关 |

## 3. 架构与约定

### 3.1 后端配置加载顺序
`database.py` 中显式实现：**优先使用 `DATABASE_URL` 环境变量**，否则构造相对路径指向 `backend-python/psi_fin.db`。这意味着：
- 本地开发：不设置任何变量即使用 SQLite 单文件数据库，零配置启动。
- Docker Compose：compose 在 `backend` 服务下拼接 `mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DATABASE}?charset=utf8mb4` 注入 `DATABASE_URL`。
- 生产/CI：只需提供 `DATABASE_URL` 即可无缝切换到 MySQL/PostgreSQL，无需改代码。

### 3.2 前端环境变量命名规范
- 所有暴露给浏览器的变量必须以 `VITE_` 开头（Vite 强制规则）。
- `VITE_BASE`：控制 Vite 构建的 `base` 路径，用于部署到 GitHub Pages 子路径 `/psi-fin/app/`。
- `VITE_API_BASE`：控制 axios baseURL，默认 `/api`（开发期由 Vite 代理到 `localhost:8000`，生产期由 nginx 反代）。
- `VITE_USE_MOCK`：字符串 `'true'` 时替换 axios adapter 为本地 mock，完全绕过后端。

### 3.3 多模式构建
`package.json` 定义了两种构建入口：
- `npm run dev`：默认 mode，使用 `.env.development`（如有）。
- `npm run build:pages`：`--mode pages`，加载 `.env.pages`，启用 Mock 并设置 base 路径。

### 3.4 环境变量来源优先级（Vite）
`loadEnv(mode, process.cwd(), '')` 会按以下顺序合并：系统环境变量 > `.env.[mode]` > `.env`，同名变量后者覆盖前者。

## 4. 约定与约束

- **数据库必须通过 `DATABASE_URL` 配置**，禁止硬编码连接串；未设置时自动降级到 SQLite，这是代码中明确实现的回退逻辑。
- **MySQL 凭据统一放在根目录 `.env`**，由 `docker-compose.yml` 通过 `${VAR:-default}` 语法注入，`.env.example` 提供模板。
- **前端环境变量必须加 `VITE_` 前缀**，否则不会被 Vite 注入到 `import.meta.env`（由 Vite 框架保证）。
- **Mock 开关是字符串比较**：`if (import.meta.env.VITE_USE_MOCK === 'true')`，因此值必须是字面量 `'true'` 而非布尔值。
- **CORS 策略固定为 `allow_origins=['*']` 且 `allow_credentials=False`**，因为前后端通过 Vite/nginx 同源代理访问，不需要 cookie 场景（见 `main.py` 注释）。
- **OpenSpec 配置**位于 `openspec/config.yaml`，仅声明 `schema: spec-driven`，与运行时配置解耦。

## 5. 缺失与局限

- 没有统一的配置模型类（如 Pydantic Settings），后端直接裸读 `os.getenv`，缺少类型校验与默认值集中管理。
- 没有 `.env.development` / `.env.production` 等多环境文件（除 `.env.pages` 外），当前仅靠单一 `.env` 和 compose 注入区分环境。
- 敏感信息（如数据库密码）以明文形式存在于 `.env.example` 中，仅作为占位符；生产应通过 CI/CD 或平台 Secrets 注入。
- 没有 feature flag 机制，行为切换仅依赖 `VITE_USE_MOCK` 一个布尔开关。
