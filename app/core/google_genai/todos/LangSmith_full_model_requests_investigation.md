# LangSmith “full model requests” 调查与后续假设

## 背景

[LangSmith 文档](https://docs.langchain.com/langsmith/trace-with-google-gemini#view-traces-in-langsmith) 声称在 LangSmith UI 中可查看：

- **Model requests: Complete prompts sent to Gemini models**（发送给 Gemini 的完整提示）

本仓库通过 `app.utils.google_genai_client.wrap_google_genai_client_with_langsmith` 使用 `langsmith.wrappers.wrap_gemini` 包装 Google GenAI 客户端。本文档记录对“完整请求”含义的排查结论及后续可验证的假设。

## 结论摘要

1. **LangSmith SDK 只包装了 `generate_content` / `generate_content_stream`**，未包装 `generate_images`（Imagen API）。因此 **Imagen 调用不会产生 LangSmith trace**，自然也没有“完整请求”可看。
2. **“完整请求”的输入来源**：wrapper 使用 `process_inputs=_process_gemini_inputs`，其输入是 `traceable` 捕获的 `generate_content(*args, **kwargs)` 的 kwargs（含 `contents`、`model`、`config` 等）。
3. **`_process_gemini_inputs` 仅对“类 dict”的 `contents` 做规范化**：当 `contents` 是 `list[dict]` 或 `str` 时会转成 `messages`；当 `contents` 是 **`google.genai.types.Content` 等 Pydantic 对象** 时，代码里 `isinstance(content, dict)` 为 False，不会进入 message 构建逻辑，最终走 fallback `return inputs`，即把原始 kwargs（含未序列化的 Content 对象）交给 LangSmith。因此 **用 `types.Content` / `Part.from_text()` 时，trace 中的“完整请求”可能不是可读的 messages，而是对象序列化结果**，取决于 LangSmith 如何序列化这些对象。
4. 现有集成测试 `test_gemini_langsmith_integration.py` 已用 `pytest.skip` 处理“trace 的 input 中未包含本次调用文本”的情况，说明 **“wrapper 未记录 messages” 的情况在现实中已出现**。

## 后续可验证假设（Hypotheses for follow-up）

以下假设可用于设计验证实验（例如本地跑一次带 trace 的调用，或在 CI 中加断言/跳过逻辑）。

---

### H1：`generate_content` 的 `contents` 为 `types.Content` 时，trace 的 input 中未规范化成 messages

- **依据**：LangSmith SDK `_process_gemini_inputs` 中仅对 `isinstance(content, dict)` 的分支构建 `messages`；`google.genai.types.Content` 是 Pydantic 模型，非 dict。
- **验证方式**：在本地用 `config.yaml.local` 跑 `test_gemini_call_trace_appears_in_langsmith`，观察是否经常被 skip；或直接查 LangSmith UI 中对应 run 的 inputs，看是否包含可读的 `messages` 还是仅见 `contents` 的 object repr。
- **若成立**：要么在应用侧先把 `contents` 转为 dict 再传（若 SDK 允许），要么向 LangSmith 提 issue / 等其支持 Pydantic Content；或在使用处手写一层把 Content 转 dict 再传给 client（需确认 google-genai 是否接受 dict）。

---

### H2：Imagen 调用（`client.models.generate_images`）完全没有被 LangSmith 记录

- **依据**：`langsmith-sdk` 源码中 `wrap_gemini` 只 patch 了 `generate_content` 与 `generate_content_stream`（含 aio），未 patch `generate_images`。
- **验证方式**：发起一次 Imagen 调用（例如通过现有 image generation API），在 LangSmith 同一 project 和时间窗口内查 runs，按 metadata（如 `source: app.utils.gemini`）过滤，应看不到与本次 Imagen 对应的 run（或只有同一流程里其他 `generate_content` 的 run）。
- **若成立**：若需在 LangSmith 中看到 Imagen 的“完整请求”（prompt、config 等），需在应用层用 `@traceable` 或自定义 span 包一层 `generate_images`，并手动记录 prompt/config 到 inputs。

---

### H3：LangSmith 对“完整请求”的展示依赖 run 的 inputs 为“消息列表”格式

- **依据**：文档称 “Model requests: Complete prompts sent to Gemini models”；LangSmith 对 LLM run 的展示通常针对 `messages` / 兼容格式优化。
- **验证方式**：同一 `generate_content` 调用，分别用（1）`contents="Say OK."` 字符串、（2）`contents=[types.Content(role="user", parts=[types.Part.from_text("Say OK.")])]` 调用，对比两次 run 在 LangSmith UI 的 “Model request” / inputs 展示是否一致、是否都易读。
- **若成立**：当 H1 成立时，使用 `types.Content` 会导致 UI 上看不到“完整请求”的友好展示；可考虑在 wrapper 上游统一把 Content 转为 dict，或改用字符串/简单 list 形式传 contents（若业务允许）。

---

### H4：`config`（如 `GenerateContentConfig`）在 trace 中只以简化形式出现，不是“完整请求”的一部分

- **依据**：SDK 中有 `_convert_config_for_tracing(kwargs)`，将 config 转为 `vars(config)` 以便 tracing；invocation params 与“发送的 prompt”可能分开存储。
- **验证方式**：在 LangSmith 中打开一次 run，查看 inputs 与 run 的 extra/invocation params，确认 system_instruction、tools、safety 等是否完整、是否在“Model requests”描述范围内。
- **若成立**：文档中的“Complete prompts”可能仅指 contents/messages，不包含 full config；若需要完整复现请求，需同时看 inputs + invocation params 或 metadata。

---

### H5：多模态（图片 + 文本）的 `contents` 在 trace 中可能不完整或不可读

- **依据**：`_process_gemini_inputs` 对 dict 形式的 parts 会处理 `inline_data`（转 base64 URL）；若 parts 是 Pydantic/ protobuf 对象而非 dict，同样不会进入该分支，图片部分可能只留下对象引用或大块 base64 被截断。
- **验证方式**：用带图片的 `types.Content`（例如 vision 描述接口）打一次 trace，检查 LangSmith 中该 run 的 inputs 是否包含图片与文本的完整、可解析结构。
- **若成立**：多模态“完整请求”可能需要应用层在 trace 中显式记录 prompt 文本 + 图片数量/占位，而不是依赖 wrapper 的自动序列化。

---

## 建议的下一步

1. **优先验证 H1 和 H2**：跑一次本地 LangSmith 集成测试 + 一次 Imagen 调用，确认 trace 是否存在、inputs 是否包含可读的 “Say OK.” / messages，以及 Imagen 是否无 run。
2. **若 H1 成立**：在代码库或 issue 中记录“当前使用 `types.Content` 时 LangSmith 可能不显示完整 messages”，并决定是否在调用前将 Content 转为 dict（需确认 google-genai API 是否支持）。
3. **若 H2 成立**：对 Imagen 在业务上需要观测时，在 `app.utils.gemini`（或调用 `generate_images` 的路径）加一层 `@traceable`，手动写入 prompt、config 摘要到 inputs/outputs。
4. **与现有 TODO 的关系**：可与 `LangSmith 追踪.md` 中“极简复刻官方示例、确保所有数据都有记录”一起做，明确“所有数据”包括：system instruction、image urls、user prompt、返回图片链接与文本，以及 Imagen 的 prompt/config（若需从 LangSmith 抽取）。

## 参考

- [Trace Google Gemini applications](https://docs.langchain.com/langsmith/trace-with-google-gemini#view-traces-in-langsmith)
- [wrap_gemini (LangSmith Python Reference)](https://reference.langchain.com/python/langsmith/wrappers/_gemini/wrap_gemini)
- LangSmith SDK 源码：`langsmith/wrappers/_gemini.py`（如 `_process_gemini_inputs`、`wrap_gemini` 仅 patch generate_content / generate_content_stream）
- 本仓库：`app.utils.google_genai_client`、`tests.app.utils.test_gemini_langsmith_integration`
