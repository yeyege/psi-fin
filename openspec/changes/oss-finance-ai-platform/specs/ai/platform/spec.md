## Purpose

提供 AI 平台层能力：统一的 LLM 适配配置与「AI 草稿 → 人工确认」安全机制，是所有 AI 场景（ChatBI、票据入账等）的公共底座，保证 AI 不直接写入任何业务/财务数据。

## ADDED Requirements

### Requirement: LLM 适配层与模型配置
系统 SHALL 通过统一 `LlmClient`（OpenAI 兼容协议）访问模型，服务端配置 `AI_BASE_URL / AI_API_KEY / AI_CHAT_MODEL / AI_VISION_MODEL` 即可切换 DeepSeek、Kimi、OpenAI、Ollama 等；AI 模块 SHALL 可通过配置开关整体停用，停用后核心 ERP 功能不受任何影响。

#### Scenario: 切换本地模型
- **WHEN** 管理员将 `AI_BASE_URL` 指向本地 Ollama 服务并保存
- **THEN** 系统 SHALL 通过连通性测试后，所有 AI 场景改由本地模型响应，无任何代码变更

#### Scenario: AI 停用降级
- **WHEN** `AI_ENABLED=false` 时用户访问 ChatBI 入口
- **THEN** 前端 SHALL 隐藏/置灰 AI 功能入口，后端 AI 路由返回 503 与可读提示

### Requirement: AI 草稿确认机制
所有 AI 生成的写操作 SHALL 先落 `ai_draft` 表（场景类型、结构化 payload、置信度、生成依据、引用素材），仅当用户在确认界面对草稿进行（可编辑后的）显式确认，才由对应业务 service 正式落库；系统 MUST 不存在任何 AI 直接写业务/财务表的代码路径。

#### Scenario: 草稿过期
- **WHEN** 草稿创建后 72 小时未确认
- **THEN** 草稿状态 SHALL 变为 expired，不可再确认，需重新生成

#### Scenario: 确认后留痕
- **WHEN** 用户确认草稿生成正式单据/凭证
- **THEN** 正式记录 SHALL 保存 `source_draft_id` 关联，且用户对该草稿的修改字段被记录在确认日志中

### Requirement: AI 调用审计
每次 LLM 调用 SHALL 记录 `ai_audit_log`：场景、模型、输入摘要（不含原始敏感数据）、耗时、token 用量/估算成本、结果状态；提供按场景聚合的用量查询接口。

#### Scenario: 用量查询
- **WHEN** 管理员查看 AI 用量页选择近 30 天
- **THEN** 系统 SHALL 展示按场景/按日的调用次数与 token 成本汇总
