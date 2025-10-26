# 代理。md·评价/（Web前端游戏工具）

本文件覆盖并补充根`AGENTS.md`，仅适用于 `evaluation/`。

## 技术栈
- Vite + React + TypeScript；接口封装在`services/`，组件放 `components/`，页面在 `pages/`。

##规定
- 仅环球统一 API 层访问；避免在组件内部直接拼接请求。
- 变更需更新对应测试（vitest），并保持类型无误与构建方式。