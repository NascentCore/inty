### 评测前端（evaluation）架构级 TODO（evaluation 根）

- [ ] 分层与目录规范：`components/`、`pages/`、`services/`、`hooks/`、`utils/` 职责边界清晰
- [ ] API 单一真源：基于 `openapi.json`/`stainless.yml` 生成 TS SDK 并接入
- [ ] 环境与配置：`import.meta.env` 统一 dev/staging/prod 基础 URL 与功能开关
- [ ] 鉴权与密钥：前端仅持 API Key；安全持久化与过期/撤销流程
- [ ] 错误处理：后端 `{code,message,details,request_id}` 模型的前端统一适配
- [ ] 请求追踪：透传并显示 `x-request-id`，便于问题定位
- [ ] 语音试听：`VoicePreviewPlayer` 预取/缓存/失败回退与可视化进度
- [ ] 头像裁切：`avatar_crop` 交互一致性与结果预览；与后端序列化字段对齐
- [ ] 流式能力：SSE/WebSocket 规范对齐（心跳/重连/鉴权/限流/取消）
- [ ] 测试策略：vitest + React Testing Library 覆盖关键组件与 hooks
- [ ] 契约/集成测试：与后端/SDK 的契约测试；Mock 与录制回放
- [ ] E2E：引入 Playwright，覆盖创建/编辑 Agent 与评测流程
- [ ] 性能：代码分割与懒加载；列表虚拟化；图片与音频缓存策略
- [ ] 无障碍与国际化：键盘可达性、ARIA 标签、文本对比度与文案本地化
- [ ] 可观测性：错误边界、日志打点、关键路径埋点（含请求耗时与状态）
- [ ] 构建与部署：Vite 构建体积治理；Docker 镜像优化；Nginx 静态与缓存
- [ ] 安全：CSP/子资源完整性；隐藏敏感信息；防止过度日志记录
- [ ] 文档化：对齐 `AGENTS.md` 的前端约定与贡献指南，更新 `docs/`
