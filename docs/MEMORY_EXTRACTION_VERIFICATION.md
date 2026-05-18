# 记忆抽取复现与验证

本文档说明如何从数据库导出用户对话、在本地复现记忆抽取流程，以及如何验证不同模型下的抽取结果。用于排查「记忆内容异常」（如存入原始对话而非摘要）、对比模型表现、验证 `_extract_part1_summary` 或 prompt 修改效果。

## 相关脚本

| 脚本 | 作用 |
|------|------|
| [tools/scripts/dump_user_messages_for_memory.py](../tools/scripts/dump_user_messages_for_memory.py) | 导出指定用户在指定时间点之前的全部对话，以及记忆抽取使用的完整 prompt |
| [tools/scripts/run_extract_memory_from_dump.py](../tools/scripts/run_extract_memory_from_dump.py) | 从导出的 prompt/JSON 按当前代码逻辑调用 LLM 抽取，输出 full_analysis 与 Part1 |

与线上抽取逻辑的关系：

- **dump** 复刻 [memory_extraction_service.get_all_messages_for_user](app/services/memory_extraction_service.py) 的 SQL 与消息解析，并拼接与 [extract_and_save](app/services/memory_extraction_service.py) 相同的 `full_prompt`。
- **run_extract** 使用同一套 [chat_completion_for_extraction](app/utils/openai_client.py)、[MEMORY_EXTRACTION_RESPONSE_FORMAT](app/services/memory_extraction_service.py)（structured output）与 [_part1_from_content](app/services/memory_extraction_service.py)（先解析 JSON 取 `part1_summary`，否则回退正则），不写 DB，仅打印/写文件。

## 1. 导出用户对话（dump）

在仓库根目录执行（需可访问数据库）：

```bash
export PYTHONPATH=.

# 必填：用户 ID；可选：配置文件、提取时间点、输出目录
python tools/scripts/dump_user_messages_for_memory.py \
  --user-id <USER_ID> \
  --config config.yaml \
  --before "2026-03-02T03:05:36" \
  --output-dir output
```

- **--user-id**：必填，目标用户 ID（如 `user-01KG1N9ETVJF57W8BD8PX00QCX`）。
- **--config**：配置文件路径，默认 `config.yaml`。脚本仅用其中的 `database.url` 直连，不触发 `app.core.config` 的模块级加载。
- **--before**：可选，ISO 时间（如 `2026-03-02T03:05:35`）。只导出该时间点之前的消息，用于精确复现某次线上抽取的输入；不传则导出全量。
- **--output-dir**：输出目录，默认 `output/`。

输出文件（以 `user_id` 后 12 位为短名）：

- `output/user_messages_<short>.json`：结构化数据（消息列表、格式化对话、chats 统计、full_prompt 长度等）。
- `output/user_messages_<short>_prompt.txt`：完整 LLM 输入 prompt，与 `extract_and_save` 中送入模型的 `full_prompt` 一致。

## 2. 从导出数据跑记忆抽取（run_extract）

在仓库根目录执行（需 `config.yaml` 且可访问 OpenRouter）：

```bash
export PYTHONPATH=.

# 方式 A：使用导出的完整 prompt 文件
python tools/scripts/run_extract_memory_from_dump.py \
  --prompt-file output/user_messages_<short>_prompt.txt

# 方式 B：使用导出的 JSON（脚本会从 formatted_chat_text 拼接 full_prompt）
python tools/scripts/run_extract_memory_from_dump.py \
  --json-file output/user_messages_<short>.json

# 将 Part1 摘要写入文件
python tools/scripts/run_extract_memory_from_dump.py \
  --prompt-file output/user_messages_<short>_prompt.txt \
  --output output/part1.txt
```

- 模型与参数：与线上一致，优先使用 `config.yaml` 中 `memory_extraction.model`，未配置则使用 [DEFAULT_MEMORY_EXTRACTION_MODEL](app/utils/openrouter_memory.py)（如 `mistralai/devstral-2512`）。
- 抽取使用 **structured output**（`response_format` + json_schema，仅 `part1_summary` 字段）；若模型不支持则自动回退为自由文本并用 `_extract_part1_summary` 解析。
- 脚本会先打印 **full_analysis**（模型完整返回，可能为 JSON 或自由文本），再打印 **Part1**（解析出的用户画像摘要）。

## 3. 验证流程（推荐步骤）

1. **确定要复现的抽取**  
   从 `memory` 表查到目标用户的 `user_id`、`memory_type=user_common` 的 `extracted_at`（以及可选 `content` 异常现象）。

2. **导出该时间点之前的对话**  
   使用 `--before` 设为该次抽取时间稍后（如 `extracted_at + 1s`），保证与当时线上读取的消息集合一致。
   ```bash
   python tools/scripts/dump_user_messages_for_memory.py --user-id <USER_ID> --before "2026-03-02T03:05:36" --output-dir output
   ```

3. **用当前默认模型跑一次**  
   ```bash
   python tools/scripts/run_extract_memory_from_dump.py --prompt-file output/user_messages_<short>_prompt.txt
   ```  
   查看终端输出的 full_analysis 与 Part1：若 full_analysis 为 JSON 且含 `part1_summary` 则走结构化解析；否则若出现大量「**AI**: / **User**:」对话复述，Part1 会退化为前 2000 字（即异常记忆来源）。

4. **换模型验证（可选）**  
   在 `config.yaml` 的 `memory_extraction` 下设置 `model: x-ai/grok-4`（或其它 OpenRouter 模型 id），保存后重新执行：
   ```bash
   python tools/scripts/run_extract_memory_from_dump.py --prompt-file output/user_messages_<short>_prompt.txt --output output/part1_grok4.txt
   ```  
   对比 Part1 是否为「**About this user, you should know:**」等结构化摘要。若新模型输出符合预期，可考虑将线上默认模型改为该模型（改 `memory_extraction.model` 或 [DEFAULT_MEMORY_EXTRACTION_MODEL](app/utils/openrouter_memory.py)）。

5. **验证 prompt/解析修改**  
   修改 [memory_extraction_prompt.txt](app/core/prompting/memory_extraction_prompt.txt) 或 [\_part1_from_content](app/services/memory_extraction_service.py) / [MEMORY_EXTRACTION_RESPONSE_FORMAT](app/services/memory_extraction_service.py) 后，用同一份 dump 的 prompt 反复执行 run_extract，对比 full_analysis 与 Part1 是否改善。

## 4. Structured output 说明

记忆抽取优先使用 **structured output**（OpenRouter/OpenAI `response_format` + `json_schema`），要求模型返回 JSON 且包含字段 `part1_summary`，从根上避免自由文本格式漂移。配置的模型需支持 [structured_outputs](https://openrouter.ai/docs/guides/features/structured-outputs)（如 **x-ai/grok-4**）。若模型不支持，API 报错后会自动回退为不传 `response_format` 再调一次，并用 `_extract_part1_summary` 解析自由文本。

## 5. 模型表现说明（经验结论）

- **mistralai/devstral-2512**（默认）：在超长上下文（如 24 万+ token）下，可能出现不按 Part 1/Part 2 结构输出、而是复述或续写 **AI**/**User** 对话的情况，导致 Part1 解析失败、存入原始对话片段。适合作为成本/延迟参考，不一定适合作为记忆抽取默认模型。
- **x-ai/grok-4**：在相同 dump 上验证可得到符合「Part 1 用户画像摘要」结构的输出，可按需设为 `memory_extraction.model` 或默认模型。

更换线上模型时，需在 `config.yaml`（或生产配置）中设置 `memory_extraction.model`，或修改代码中的默认模型常量并部署。

## 6. 相关代码与文档

- 记忆功能总览：[evaluation/docs/MEMORY_FEATURE_IMPLEMENTATION_SUMMARY.md](evaluation/docs/MEMORY_FEATURE_IMPLEMENTATION_SUMMARY.md)
- 抽取与解析逻辑：[app/services/memory_extraction_service.py](app/services/memory_extraction_service.py)
- 抽取用 LLM 调用：[app/utils/openai_client.py](app/utils/openai_client.py)（`chat_completion_for_extraction`）
- 默认模型常量：[app/utils/openrouter_memory.py](app/utils/openrouter_memory.py)
- 手动对单用户执行抽取（写 DB）：[tools/scripts/run_memory_extraction.py](../tools/scripts/run_memory_extraction.py)（`--user-id`，可选 `--dry-run`）

## 7. 记忆抽取工作流模式（新增）

`memory_extraction.workflow_mode` 支持 2 种值：

- `always_summarize_full_chat_messages_history`（默认，原有逻辑不变）  
  每次抽取读取用户全量历史消息，直接生成并覆盖 `user_common`。
- `daily_incremental_summarization`（增量模式）  
  每日读取用户前一 UTC 日消息，先生成 daily profile，再基于「旧 `user_common` + daily profile」更新并覆盖 `user_common`。

验证增量模式时，建议在 `config.yaml` 中先设置：

```yaml
memory_extraction:
  enabled: true
  workflow_mode: daily_incremental_summarization
```
