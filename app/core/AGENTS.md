# 核心 AI 组件

应该重命名为 AI

## 用户信息与聊天 prompt

- `_get_user_profile_sync` 构建的 ##User Information 会包含 `users.meta_data` 中的 MBTI（当存在时）；该段作为 system message 注入到聊天 prompt，供所有 agent（含官方助手）使用。
