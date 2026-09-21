---
kind: error_handling
name: FastAPI 全局异常 + 前端 Axios 拦截器的统一错误处理
category: error_handling
scope:
    - '**'
source_files:
    - backend-python/app/common/errors.py
    - backend-python/app/main.py
    - backend-python/app/services/auth_service.py
    - frontend-vue/src/api/client.ts
    - frontend-vue/src/api/index.ts
---

## 1. 整体方案

后端基于 FastAPI，前端基于 Vue3 + Axios。错误处理采用「业务异常类 + 全局异常处理器」在后端集中转换，配合前端的 Axios 响应拦截器统一处理网络与鉴权错误。

- 后端自定义异常：`app/common/errors.py` 中的 `BusinessError(Exception)`，携带 `message` 和 `status`（默认 400）。
- 全局异常处理器：在 `app/main.py` 中通过 `@app.exception_handler(BusinessError)` 将 `BusinessError` 转为 JSON 响应 `{"detail": ..., "message": ..., "data": None}`，与 router 层直接返回的 `{code, message, data}` 风格保持一致（由前端按 `code`/`message`/`data` 字段消费）。
- 鉴权相关错误使用 FastAPI 内置 `HTTPException`（401/403），由 FastAPI 默认处理器输出标准格式。
- 前端通过 `axios.create()` 的响应拦截器统一处理：401 时清除本地 token 并跳转登录页；其他错误打印 `console.error('API Error:', msg)` 并 `Promise.reject` 回传给调用方。

## 2. 关键文件与位置

| 文件 | 职责 |
|---|---|
| `backend-python/app/common/errors.py` | 定义 `BusinessError` 业务异常基类 |
| `backend-python/app/main.py` | 注册 `BusinessError` 的全局异常处理器、CORS 中间件 |
| `backend-python/app/services/auth_service.py` | 使用 `BusinessError` 表达业务校验失败（用户名重复、用户不存在、账号停用等），使用 `HTTPException` 表达鉴权失败 |
| `frontend-vue/src/api/client.ts` | Axios 实例：请求拦截自动附加 Bearer token，响应拦截统一提取 `data`、处理 401 并转登录页 |
| `frontend-vue/src/api/index.ts` | 各模块 API 函数，约定返回 `{code, message, data}` 结构，调用方据此判断成功/失败 |

## 3. 架构与约定

### 后端异常分层
- **业务异常**：在 service 层抛出 `BusinessError(message, status)`，如 `auth_service.py` 中：
  - 用户名已存在 → `BusinessError(..., 409)`
  - 用户不存在 → `BusinessError("用户不存在", 404)`
  - 密码错误 → `BusinessError("用户名或密码错误", 401)`
  - 账号停用 → `BusinessError("账号已停用，请联系管理员", 403)`
  - 最后一个管理员保护 → `BusinessError("不能停用或降级最后一个启用管理员", 409)`
- **鉴权异常**：在依赖注入 `get_current_user` / `require_admin` 中抛 `HTTPException(401/403)`，因为依赖注入中的异常不会被 router 层 try/except 捕获（代码注释明确说明）。
- **全局转换**：`business_error_handler` 把 `BusinessError` 映射为 `{detail, message, data: None}`，与 router 正常返回的 `{code, message, data}` 保持字段兼容。

### 前端错误处理
- 所有 HTTP 请求走 `api`（`client.ts` 创建的 axios 实例），统一配置 `timeout: 10000`（登录接口覆盖为 60s 以适配 Serverless 冷启动）。
- 请求拦截器：从 `localStorage.getItem('psifin_token')` 读取 token 并附加到 `Authorization: Bearer <token>`。
- 响应拦截器：
  - 成功：返回 `res.data`（即后端 `{code, message, data}` 的 data 字段）。
  - 失败：若 `error.response.status === 401`，清除 `psifin_token` 与 `psifin_user`，并强制跳转到 `#/login`；否则记录 `console.error('API Error:', msg)` 后 reject。
- 各 API 函数（`index.ts`）类型声明期望返回 `{code: number; data: ...}`，调用方据此判断业务状态码。

### 无 panic/recover 模式
Python 侧不使用 `try/except` 包裹每个路由，而是依赖 FastAPI 的全局异常处理器；前端也不使用 `try/catch` 包装所有调用，而是依赖 Axios 拦截器统一处理 401，业务逻辑自行处理非 401 的错误分支。

## 4. 约定与约束

- **业务错误必须通过 `BusinessError` 抛出**，禁止在 router 层手动构造 JSONResponse——由全局处理器统一格式化。
- **鉴权失败统一用 `HTTPException(401/403)`**，不混用 `BusinessError`，以便 FastAPI 默认处理器输出标准鉴权错误。
- **前端 401 是全局可恢复错误**：任何接口返回 401 都会触发清 token + 跳转登录，无需在每个视图单独处理。
- **超时策略**：普通请求 10s，登录与 `/health` 预热请求 60s（Serverless 冷启动场景），在 `index.ts` 中针对特定接口覆盖 `timeout`。
- **Mock 模式下的错误**：当 `VITE_USE_MOCK=true` 时，Axios adapter 替换为 `mockAdapter`，所有网络错误被 Mock 数据替代，不影响真实部署时的错误处理路径。
- **健康检查 `/api/health` 刻意不查库、不鉴权**，用于前端登录页预热与外部保活脚本，避免误报错误。

该方案在后端实现了「业务异常集中转换」，在前端实现了「鉴权错误集中处理」，两者通过统一的 `{code, message, data}` 响应契约衔接。