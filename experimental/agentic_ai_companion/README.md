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

- **工具**：当前支持 `send_app_icon`、`send_zun_long_photo`、`send_selfie_photo`、`generate_image`、`text_to_speech`、`live_voice_message_reply`、`erotic_scene_generate`。`generate_image` 已按 `app/` 聊天生图思路实现：基于最近 10 条对话构建 chat-to-image 提示词，并优先使用 `companion_profile` 与 `user_profile` 的参考图（可被工具参数覆盖）生成 intimacy role-play 场景图；若生图失败则直接返回错误，不再自动重试备用模型或复用历史图。执行后仍会再调用 LLM 输出文字以配合图片。`text_to_speech` 将 LLM 返回的文本转为语音（Gemini TTS），生成 WAV 文件，适合精确朗读给定句子；`live_voice_message_reply` 使用 Gemini Live API，带系统指令与最近 10 条消息上下文，生成更自然、对话式的短语音消息（类似微信语音消息，点击播放），与 TTS 对比用于验证 Live 语音能力；`erotic_scene_generate` 在对话暗示用户亢奋或用户明确要求亲密/色情场景时，根据最近对话生成连续多段**文字** scene 描述，仅文字、不生成图片，无需用户输入 continue。上述 Gemini 相关工具均需在 `.env` 中配置 `GEMINI_API_KEY`。REPL 中打印图片或语音的绝对路径，用户可在终端中点击路径自行打开查看或播放。

## 快速开始

在仓库根目录执行（当前入口为 `main.py`，最小化 role play 示例）：

```bash
# 同步模式（传统 REPL，等待用户输入后回复）
python -m experimental.agentic_ai_companion.main

# Heartbeat 模式（Agent 始终在线，定期主动发消息）
python -m experimental.agentic_ai_companion.main --heartbeat

# 自定义心跳间隔（默认 120 秒）
python -m experimental.agentic_ai_companion.main --heartbeat --heartbeat-interval 60
```

### 实验性：记忆压缩（Memory Compaction）

长对话时可开启实验性记忆压缩（分层 episodic + semantic + running summary）：

```bash
python -m experimental.agentic_ai_companion.main \
  --enable-memory-compaction \
  --memory-max-context-chars 9000 \
  --memory-keep-recent-messages 18 \
  --memory-max-messages-per-episode 8
```

- 设计与调研结论见：`FR_MEMORY_COMPACTION_STRATEGY.md`
- 默认关闭，避免影响现有对话行为
### Heartbeat 模式

使用 `--heartbeat` 启动后，Agent 不再仅等待用户输入。每隔一段时间（默认 120 秒），系统会向 LLM 注入一条 `[SYSTEM HEARTBEAT]` 信号，LLM 根据对话上下文、角色性格和时间流逝决定是否主动发消息：
- 有话说时：自然地输出主动消息（问候、分享想法、追问等）
- 无话说时：回复 `[SILENT]`，终端无任何输出
- 连续静默超过阈值后，心跳间隔自动延长（指数退避），达到上限后暂停心跳直到用户下次输入

## 如何测试 live_voice_message_reply

**环境**：在仓库根目录或 `experimental/agentic_ai_companion/` 下配置 `.env`（或 export），需包含 `GEMINI_API_KEY` 与 `OPENROUTER_API_KEY`。

**方式一：REPL 手动触发**

1. 从仓库根目录运行：`python -m experimental.agentic_ai_companion.main`（可选加 `--debug` 看日志）。
2. 在提示符输入一句会促使模型调用语音消息工具的话，例如：
   - "Send me a short voice message saying hello."
   - "Reply with a voice message."
   - "I want to hear a voice message from you."
3. 若模型调用 `live_voice_message_reply`，终端会打印工具结果与 WAV 绝对路径；在终端或文件管理器中打开该路径即可播放。

**方式二：仅测 Live API 语音生成（不经过 REPL/OpenRouter）**

在仓库根目录执行下面脚本，用最小上下文调用 `generate_speech_via_live`，检查是否生成 WAV（需 `GEMINI_API_KEY`）：

```bash
cd /path/to/agent-ai-companion
python -c "
import asyncio
from experimental.agentic_ai_companion.live_voice import generate_speech_via_live
from google.genai import types

async def run():
    sys = types.Content(parts=[types.Part.from_text(text='You are a friendly assistant.')], role='user')
    msgs = [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}]
    pcm, transcript = await generate_speech_via_live('Say hello in a short voice message.', messages=msgs, system_instruction=sys)
    print('PCM length:', len(pcm), 'Transcript:', repr(transcript))
    from pathlib import Path
    out = Path('experimental/agentic_ai_companion/tmp/test_live.wav')
    out.parent.mkdir(parents=True, exist_ok=True)
    import wave
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    print('Wrote', out)

asyncio.run(run())
"
```

播放生成的 `tmp/test_live.wav` 即可确认 Live 语音输出是否正常。

## 工具定义

分层定义：

1. 描述工具本身的功效：只介绍工具输入、输出、做了什么
2. 描述工具意图：目的是什么

这样方便 AI 自由决策

## 第一迭代计划（仅更新计划，不写代码）

目标：在终端原型中验证“多代工具”对 LLM 调用的影响，确保低成本工具优先、必要时再升级到高代工具。

**generate_image 设计意图**：`generate_image` 为 non-TERMINAL 工具。执行后不会立即返回用户，而是再调用 LLM 根据生成的图片输出一段文字（如对图片的解读或情感表达），以配合图片给出更自然的回复。

## 参考资料

[OpenRouter 工具调用](https://openrouter.ai/docs/guides/features/tool-calling#best-practices-and-advanced-patterns)
[OpenAI SDK 工具调用](https://developers.openai.com/api/docs/guides/tools)
[Google GenAI SDK](https://ai.google.dev/gemini-api/docs/imagen)

### LangSmith 追踪

设置 `LANGSMITH_TRACING=true` 和 `LANGSMITH_API_KEY` 后，Chat Completion（OpenRouter）调用会出现在 [LangSmith](https://smith.langchain.com) 对应 project 中（默认 `LANGSMITH_PROJECT=agentic-ai-companion`）。用于排查空回复、错误 tool call、token 使用等。不设则不发送 trace。

Imagen、TTS 的 Gemini 调用需 `langsmith>=0.4.33` 才会上报；若当前环境为较低版本，会使用未包装的 client，仅 OpenRouter 被追踪。

参考链接：[LangSmith for Gemini](https://docs.langchain.com/langsmith/trace-with-google-gemini)、[LangSmith for OpenAI](https://docs.langchain.com/langsmith/trace-openai)

### 可能的高级扩展

- Tavus [实时多模态感知系统、细节表情、语调、等等跟踪](https://www.tavus.io/post/raven-1-bringing-emotional-intelligence-to-artificial-intelligence)
  - [HackerNews 讨论](https://news.ycombinator.com/item?id=46965012)
  - [示例](https://raven.tavuslabs.org/)
