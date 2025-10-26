# AGENTS.md · evaluation/（Web 前端评测工具）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `evaluation/`。

## 技术栈
- Vite + React + TypeScript；接口封装在 `services/`，组件放 `components/`，页面在 `pages/`。

## 约定
- 只经由统一 API 层访问后端；避免在组件内直接拼接请求。
- 变更需更新对应测试（vitest），并保持类型无误与构建通过。
