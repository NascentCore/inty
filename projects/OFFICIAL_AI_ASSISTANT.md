CREATED_BY_AGENT

# OFFICIAL AI ASSISTANT 设计概要

## 概述
- 将底部中间的 **Create** tab 替换为 **IntelliMate** 官方助手入口。
- 点击入口进入官方助手的专属聊天页，首屏风格参考 Gemini 的欢迎页。

## 入口与导航
- 底部 Tab 图标使用应用官方 icon。
- 入口点击后导航到官方 IntelliMate 角色聊天页：
  - agentId 使用官方 IntelliMate 常量。
  - 进入时不自动聚焦输入框，保持欢迎页完整展示。
  - fromPage 记录为 `official_assistant_tab`，便于埋点区分来源。

## 欢迎页结构（无历史对话时显示）
- 顶部问候语 + 副标题（示例：`Hi` / `Where should we start?`）。
- 右侧显示应用 icon。
- 下方展示多枚圆角快捷入口（Chip 风格）。

## 快捷入口与交互
- 快捷入口用于**预填提示词**，点击即把文案写入输入框并聚焦。
- 当前提供的快捷入口：
  - Create a character
  - Explore characters
  - Write a story

## 显示条件
仅在以下条件同时满足时展示欢迎页：
- 当前聊天为 IntelliMate 官方角色；
- 聊天记录中没有真实对话消息（仅开场白/系统消息视为无对话）。

## 设计约束
- UI 尺寸与间距统一使用 `UiConfigs` 中的配置项。
- 文案使用 `strings.xml` 资源，避免硬编码。
