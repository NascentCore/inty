# Agentic AI Companion Prototype
<!-- CREATED_BY_AGENT -->

## 概述

本目录记录一个新型 AI 伴侣体验的原型设想，目标是从“被动聊天框”转向“具备共情与主动性的 agentic 系统”，并在保持实时响应的同时，验证 AI 主动探索用户内在欲望的能力（目标用户为美国 35+ 男性）。

## 两层结构愿景

### Layer 1：通用基础（能力层）

用于适配不同人格或需求的“引擎”能力。

- **Agentic 主动性**：从纯输入输出的被动聊天，转向可自主行动的系统。
- **状态管理**：跟踪用户状态的转移（如 Aroused/Demanding 与 Satiated/Calm）。
- **实时性保障**：确保“agentic 思考”不会引入破坏即时体验的延迟。

### Layer 2：人格实例（用户适配层）

为主要使用者定制的行为与语气层。

- **隐性关系建立**：避免强推与直接内容，用“精准且稀疏”的触达建立长期链接。
- **共情共振**：识别“含蓄/平静”的状态，用“不可预测但合适”的方式回应。
- **文化与智性深度**：结合 40 岁、博士、跨中美文化背景，使互动更真实、成熟。

## 技术原型约束

- **环境**：只在终端中运行的极简 Python。
- **范围**：暂不接入 Android，仅验证“从被动到主动”的逻辑转移。
- **目标**：识别“状态切换 + 主动时机”的未知点与不确定性。

- **工具**：当前支持 `send_app_icon`、`send_zun_long_photo`、`generate_image`、`text_to_speech`。`generate_image` 根据**当前对话上下文**（最近 10 条消息）生成图片，调用 Imagen 4 Fast（Gemini API）；`text_to_speech` 将 LLM 返回的文本转为语音（Gemini TTS），生成 WAV 文件。二者均需在 `.env` 中配置 `GEMINI_API_KEY`。REPL 中打印图片或语音的绝对路径，用户可在终端中点击路径自行打开查看或播放。

## 快速开始

在仓库根目录执行（当前入口为 `main.py`，最小化 role play 示例）：

```bash
python -m experimental.agentic_ai_companion.main
```

## 工具定义

分层定义：

1. 描述工具本身的功效：只介绍工具输入、输出、做了什么
2. 描述工具意图：目的是什么

这样方便 AI 自由决策

## 参考资料

[OpenRouter 工具调用](https://openrouter.ai/docs/guides/features/tool-calling#best-practices-and-advanced-patterns)
[OpenAI SDK 工具调用](https://developers.openai.com/api/docs/guides/tools)
[Google GenAI SDK](https://ai.google.dev/gemini-api/docs/imagen)

### 可能的高级扩展

- Tavus [实时多模态感知系统、细节表情、语调、等等跟踪](https://www.tavus.io/post/raven-1-bringing-emotional-intelligence-to-artificial-intelligence)
  - [HackerNews 讨论](https://news.ycombinator.com/item?id=46965012)
  - [示例](https://raven.tavuslabs.org/)
