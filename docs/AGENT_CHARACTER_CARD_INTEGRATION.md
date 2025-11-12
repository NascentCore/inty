# Agent系统角色卡集成方案

## 概述

本文档说明 InTy 后端如何将 SillyTavern V2 角色卡字段无缝集成到聊天系统中，覆盖数据落库、提示词组装、实例缓存与导入导出流程。目标是为开发者提供一份与当前代码实现保持同步的参考，避免沿用已经废弃的字段（如 `first_message` 列）或早期的 LangGraph 示意代码。

## 术语与关键字段

- **用户（user）**：发起聊天的终端用户。
- **角色（agent）**：用户聊天的 LLM 智能体，存储于 `agents` 表。
- **角色卡（character card）**：SillyTavern 定义的角色描述规范，支持 JSON 与嵌入 PNG。
- **主提示词（main_prompt）**：系统级提示词，位于第一条 system message。
- **模式提示词（mode_prompt）**：用于普通/会员模式切换的系统提示词。
- **角色性格与场景（personality/scenario）**：角色卡核心上下文，作为额外 system message 注入。
- **对话示例（message_example）**：角色对话风格示例，在提示词中以 system message 提供参考。
- **角色介绍（intro）**：展示于前端，同时在聊天时尾部追加为 system message。
- **开场白（opening）**：面向用户的首句文本，并驱动开场白语音生成；不再注入系统提示词。
- **替代问候语（alternate_greetings）**：角色卡中额外问候语，存储在 JSON 字段内。

> ⚠️ `first_message` 数据仅保留在角色卡原始 JSON 内，数据库字段已在 2025-07 中移除；所有需要的开场白请使用 `opening` 或 `alternate_greetings`。

## 架构总览

1. **数据写入**：创建/导入角色时，Pydantic 层（`app/schemas/agent.py`）接收角色卡字段，持久化到 `agents` 表对应列或 `settings`/`character_card_data` JSON。
2. **实例缓存**：`AgentManager` 根据数据库数据实例化 `Agent` 对象，并缓存以降低后端压力。
3. **提示词组装**：`Agent.build_system_messages` 将主提示词、角色卡上下文、模式提示词、用户信息与 `intro` 依次拼装成系统消息列表。
4. **聊天执行**：`Agent._chat_sync_optimized` 结合聊天历史与最新用户消息调用 OpenAI/OpenRouter 接口，返回回复并写入历史。
5. **导入导出**：`CharacterCardService` 负责角色卡与 Agent 数据的互相转换，保持 SillyTavern V2 兼容。

## 数据存储与字段映射

`app/models/agent.py` 定义了角色卡相关列：`personality`、`scenario`、`message_example`、`creator_notes`、`post_history_instructions`、`alternate_greetings`、`character_book`、`tags`、`character_version`、`extensions` 及角色基础信息等，同时保留 `character_card_data` 以原样持久化导入的 JSON。

角色卡字段与后端字段映射如下：

| SillyTavern 字段 | 后端字段 | 说明 |
| --- | --- | --- |
| `name` | `agents.name` | 角色名（≤30 字符） |
| `description` | `agents.intro` | 角色简介，同时参与系统消息构建 |
| `personality` | `agents.personality` | 角色性格 system message |
| `scenario` | `agents.scenario` | 场景设定 system message |
| `mes_example` | `agents.message_example` | 对话示例 system message |
| `creator_notes` | `agents.creator_notes` | 创作者备注 |
| `post_history_instructions` | `agents.post_history_instructions` | 历史后指令 |
| `alternate_greetings` | `agents.alternate_greetings` | 备用问候 |
| `character_book` | `agents.character_book` | 世界设定（JSON） |
| `tags` | `agents.tags` | 标签数组 |
| `character_version` | `agents.character_version` | 版本标识 |
| `extensions` | `agents.extensions` | 前后端约定的扩展容器 |
| `first_mes` | `agents.opening` + `character_card_data.data.first_mes` | 作为开场白文本，不再单独存列 |

## 提示词组装流程

实例化后的 `Agent` 会在聊天前调用 `build_system_messages`，生成系统消息序列。字段注入顺序如下：

1. 主提示词：若配置强制使用全局默认则使用 `PURITY_ROLEPLAY_PROMPT`，否则按角色自定义或 `ROMANTIC_ROLEPLAY_PROMPT`。
2. 角色卡上下文：`personality` → `scenario` → `message_example`，逐条渲染 `{{ char }}` 与 `{{ user }}`。
3. 模式提示词：根据 `chat_settings.premium_mode` 选择 premium/normal 模式提示词，并进行模板渲染。
4. 样式提示词（可选）：如果聊天设置存在 `style_prompt`，直接追加。
5. 用户画像：`_get_user_profile_sync` 从数据库与缓存中拼接 `Name/Gender/Age/Description` 信息。
6. 角色介绍：`intro` 作为系统消息末尾补充角色语气设置。

核心实现位于 `app/core/agent/agent.py`：

```300:329:app/core/agent/agent.py
        system_messages.append(SystemMessage(content=rendered_main_prompt))
        character_messages = self._build_character_context(user_name=user_name)
        system_messages.extend(character_messages)

        if chat_settings and chat_settings.premium_mode:
            mode_prompt = prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt
        else:
            mode_prompt = self._get_effective_mode_prompt()
        rendered_mode_prompt = prompt_template.render_prompt_jinja2_template(
            tmpl=mode_prompt, char=self.name, user=user_name
        )
        system_messages.append(SystemMessage(content=rendered_mode_prompt))

        if chat_settings and chat_settings.style_prompt:
            system_messages.append(SystemMessage(content=chat_settings.style_prompt))
        if user_profile:
            system_messages.append(SystemMessage(content=user_profile))
        if self.intro:
            system_messages.append(SystemMessage(content=self.intro))
```

## 聊天执行流程

`Agent.chat`（现标记为 deprecated，核心逻辑在 `_chat_sync_optimized`）负责将系统消息、历史消息与最新请求拼装后调用 OpenAI 客户端。

主要步骤：

1. 通过 `AgentManager.get_agent` 获取实例并更新最后使用时间。
2. 利用 `PostgresChatMessageHistory` 读取历史消息，并在必要时做截断（默认保留全部）。
3. 将系统消息与历史、用户消息拼接为 LangChain `BaseMessage` 列表，再转换为 OpenAI 格式。
4. 通过复用的 `OpenAI` 客户端发起 `chat.completions.create` 请求，同时附带 `user` 字段用于用量追踪。
5. 将模型回复写入历史表，并返回文本内容。

历史与提示词拼接逻辑位于：

```546:692:app/core/agent/agent.py
        recent_history = self._get_relevant_history(history.messages)
        all_messages = recent_history + messages["messages"]
        history.add_messages(messages["messages"])

        system_messages = self.build_system_messages(user_profile, chat_settings)
        messages: list[BaseMessage] = system_messages + all_messages
        openai_messages = [
            langchain_message_to_openai_message(message, user_name, self.name)
            for message in messages
        ]
        response = client.chat.completions.create(
            messages=openai_messages,
            model=self.model_config.get("model", default_model),
            temperature=self.model_config.get("temperature", default_temperature),
            max_tokens=self.model_config.get("max_tokens", default_max_tokens),
            top_p=self.model_config.get("top_p", default_top_p),
            extra_body={"generation_config": {"thinking_budget": 0}, "user": user_id},
        )
        history.add_messages([AIMessage(content=response_text)])
```

## AgentManager 缓存策略

`AgentManager` 负责实例复用、并发安全以及闲置清理：

- 使用读写锁与 `agent_id` 维度的互斥锁避免重复创建；
- 超过缓存上限时淘汰最久未使用实例；
- 每小时异步清理超过 `max_idle_time` 的 Agent；
- 提供 `reload_agent` 与 `initialize_popular_agents` 满足热加载与预热需求。

实例化时会注入角色卡字段与提示词配置：

```928:967:app/core/agent/agent.py
                    agent = Agent(
                        agent_id=agent_id,
                        name=agent_name,
                        model_config=model_config,
                        description=description,
                        main_prompt=agent_data.get("main_prompt", ""),
                        mode_prompt=agent_data.get("mode_prompt", ""),
                        personality=agent_data.get("personality", ""),
                        scenario=agent_data.get("scenario", ""),
                        message_example=agent_data.get("message_example", ""),
                        creator_notes=agent_data.get("creator_notes", ""),
                        tags=agent_data.get("tags", []),
                        character_version=agent_data.get("character_version", "1.0"),
                        extensions=agent_data.get("extensions", {}),
                        intro=agent_data.get("intro", ""),
                    )
                    self.agents[agent_id] = agent
```

## 角色卡导入与导出

`CharacterCardService` 和 `CharacterCardMapper` 负责角色卡和 Agent 之间的转换：

- **导入**：解析 JSON/PNG→`CharacterCardV2`→`map_card_to_agent`→按需剥离 `character_book`、`alternate_greetings`→写入数据库。
- **导出**：从数据库读取 Agent→按请求过滤可选字段→`map_agent_to_card`→返回标准 V2 结构。
- 导入时生成 `opening` 与 `intro`，并保留原始角色卡 JSON 以便无损导出。

```51:82:app/services/character_card_mapper.py
        agent_data = {
            "id": agent_id,
            "name": data.name[:30],
            "gender": self._infer_gender(data),
            "intro": data.description,
            "opening": (
                data.first_mes or data.alternate_greetings[0]
                if data.alternate_greetings
                else ""
            ),
            "prompt": self._build_system_prompt(data),
            "character_card_spec": card_data.spec.value,
            "character_card_data": card_data.dict(),
            "personality": data.personality,
            "scenario": data.scenario,
            "message_example": data.mes_example,
            "creator_notes": data.creator_notes,
            "post_history_instructions": data.post_history_instructions,
            "alternate_greetings": data.alternate_greetings,
            "character_book": (
                data.character_book.dict() if data.character_book else None
            ),
            "tags": data.tags,
            "character_version": data.character_version,
            "extensions": data.extensions,
        }
```

## 测试与验证建议

- **单元测试**：覆盖 `CharacterCardMapper` 映射、提示词模板渲染（含变量替换）、用户信息解析。
- **集成测试**：验证 `import-character-card`、`export-character-card`、`character-card/features` 接口，以及聊天流程中系统消息顺序是否符合预期。
- **回归测试**：确保无角色卡字段的旧 Agent 仍能成功聊天，缓存命中后配置变更可通过 `reload_agent` 生效。
- **监控**：关注 token 消耗、缓存命中率、`AgentManager` 清理日志与异常。

## 已知约束与后续工作

- `first_message` 字段已移除；若仍需在数据库中持久化该信息，需要评估是否放入 `extensions` 或 `character_card_data`。
- 聊天流程仍是同步阻塞 OpenAI API，后续可在 `_chat_sync_optimized` 中接入流式接口或重构为 Runnable 管线。
- `Agent.get_final_prompt` 仍引用 `self.prompt_runnable`（尚未完全实现），如需调试完整提示词可进一步补强该逻辑。
- 语音系统依赖 `opening` 文本，在导入角色卡后建议触发 `generate_agent_opening_voice` 以保持体验一致。
