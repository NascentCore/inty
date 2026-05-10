# iMate智能体陪伴系统点子

1. [claude-mem](https://github.com/thedotmack/claude-mem)机制引入到agentic-kernel，Claude Code上一种非常有效的记忆管理插件。
2. [Human-like Memory](https://plugin.human-like.me/docs?tab=api&locale=zh-CN) 提供 Search/Add REST API（x-api-key），可作 companion 工作区记忆的外挂检索与异步写入补充层，而非替换基于分层 Markdown 与 companion_workspace 版本表的现有策展管线。
3. 将 `/experimental/agentic_ai_companion` 中尚未进入内核的能力（如情感状态枚举、`scene_gen` 文字亲密场景、Live 语音条原型语义）按产品边界收口进 `app/core/agentic_kernel`，并与现有 `heartbeat`、`transcript_compaction`、`app/core/voice` 路径对齐后再移除实验目录。
