---
kind: logging_system
name: PSI-FIN 日志系统：无结构化日志框架，仅依赖标准库 print 与浏览器 console
category: logging_system
scope:
    - '**'
source_files:
    - backend-python/app/main.py
    - backend-python/init_data.py
    - frontend-vue/src/api/client.ts
---

## 1. 使用的系统/方案

本仓库**没有引入任何第三方日志框架**。后端 Python 部分未配置 `logging`、`loguru`、`structlog` 等模块；前端 Vue 部分也未集成 `loglevel`、`pino`、`winston` 等日志库。整体采用最简方式输出日志。

- **后端（FastAPI）**：通过 Python 内置的 `print()` 直接输出到标准输出，由运行环境（Docker / Vercel Serverless）收集 stdout/stderr。所有业务初始化脚本（如 `backend-python/init_data.py`）使用 `print("示例数据已存在，跳过初始化")` 等形式打印进度。
- **前端（Vue + Axios）**：在统一请求客户端 `frontend-vue/src/api/client.ts` 的响应拦截器中，对网络错误调用 `console.error('API Error:', msg)` 输出错误信息；其余代码未发现其他 `console.log/info/warn/debug` 调用。

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `backend-python/app/main.py` | FastAPI 应用入口，注册路由、异常处理器、CORS，但**未配置任何日志中间件或全局 logger** |
| `backend-python/init_data.py` | 启动时预置数据的脚本，全部使用 `print()` 输出初始化过程 |
| `frontend-vue/src/api/client.ts` | Axios 实例定义，唯一的前端日志点：401 及网络错误时 `console.error` |

## 3. 架构与约定

- **无集中式日志初始化**：没有在 `app/__init__.py`、`app/database.py` 或其他公共模块中创建 logger 实例，也没有设置日志级别、格式化器、handler 或 sink。
- **无结构化字段**：日志输出为纯文本字符串，不包含 JSON 结构、trace_id、request_id、user_id、correlation_id 等上下文字段。
- **无日志级别管理**：未区分 INFO/WARN/ERROR/DEBUG，所有 `print()` 和 `console.error()` 都视为同等严重性。
- **无日志路由/落盘策略**：后端不将日志写入文件、数据库或外部服务（如 ELK、Sentry、阿里云日志），完全依赖容器/平台的标准输出聚合。
- **异常处理中的日志缺失**：`main.py` 中对 `BusinessError` 的异常处理器只返回 JSON 响应，**没有记录异常堆栈或请求上下文**。

## 4. 约定与约束

- **后端日志输出位置**：所有业务日志通过 `print()` 输出到 stdout，由部署环境（Dockerfile 中的 CMD/ENTRYPOINT、Vercel Serverless 运行时）负责收集。该模式适合轻量演示项目，但不支持按级别过滤或持久化。
- **前端错误日志位置**：仅在 API 层统一捕获并输出 `console.error`，业务组件内部未自行打点，便于集中排查网络问题。
- **无强制规范**：仓库中没有 `.eslintrc` 规则禁止 `console.log`，也没有 Python lint 规则要求使用 `logging` 模块；当前行为是“自然形成”的约定而非 enforced 规则。
- **可观测性缺口**：由于缺少 trace_id/correlation_id 注入、请求链路追踪和结构化输出，跨进程/跨服务的日志关联无法实现。

综上，该项目的日志系统处于**最小可用状态**——仅满足本地调试和基础错误定位需求，尚未达到生产级可观测性标准。