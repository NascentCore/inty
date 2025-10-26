### 跨端 API 与架构改进 TODO（仓库根）

- [ ] 定义 OpenAPI 单一真源，自动生成 Kotlin/TS/Python SDK
- [ ] 启用 API 版本化策略（路径 /api/v1、弃用流程与稳定期）
- [ ] 环境与配置一致性：统一 dev/staging/prod 基础 URL 与功能开关
- [ ] 统一鉴权：Bearer + 刷新 Token；Android 侧一致的持久化与轮换
- [ ] 标准错误响应：{code, message, details, request_id}；App 侧统一适配
- [ ] 重试与幂等：写操作幂等键；网络重试采用指数退避 + 抖动
- [ ] 请求追踪：x-request-id/traceparent 贯穿 App⇄后端；接入 OpenTelemetry
- [ ] 统一网络栈/SDK：Android 仅保留单一 SDK，移除双栈分裂
- [ ] 合同测试：在 CI 中运行契约测试，阻止破坏性变更合入
- [ ] 性能与可靠性：HTTP/2 与 gzip；分页/游标统一；限流与配额错误码
- [ ] 媒体与流式：语音/图像接口稳定化；进度与流式响应（SSE/WebSocket）规范
- [ ] 安全与合规：RAI 过滤结果透传；审计日志；请求大小与速率限制
- [ ] 发布流程：变更记录与迁移指南自动生成并随 SDK 发布
