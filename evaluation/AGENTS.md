# AGENTS.md · evaluation/（Web 前端评测工具）

这是一个用于支持 IntelliMate 产品运营的 web 工具；用户是产品经理（非工程师）；为他们提供角色管理、用户行为分析等等核心功能。

- Do not add error handling, assumes user will retry
- 只经由统一 API 层访问后端；避免在组件内直接拼接请求。
- 变更需更新对应测试（vitest），并保持类型无误与构建通过。
- 图片都保证完整显示
- **Assume user**：仅超级用户可见。在页面头「Assume user」下拉中选择任意已录用户后，单角色聊天与语音通话会以该用户身份加载/使用其与角色的对话历史；后端通过 `X-Assume-User-Id`（HTTP）与 `assume_user_id`（WebSocket）识别。
