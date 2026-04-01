# FR_INTY_V2_INTEGRATION_CONTRACTS

## 1. 目标

- 冻结 `inty_v2_text_chat_prototype` 作为整合主干前的核心契约。
- 为后续 Phase 1-4 提供不变量，防止多来源实验代码并入时破坏主链路。

## 2. Turn 契约（输入/输出）

### 2.1 Turn Input（内部）

- `workspace`: 工作目录根路径。
- `user_text`: 当前轮用户文本；heartbeat 回合由系统合成文本替代。
- `heartbeat_turn`: 是否为陪伴心跳回合。
- `debug_print_system`: 是否打印 system prompt（仅调试）。
- `defer_memory_update`: 是否延后记忆管线执行。
- `llm_trace`: 是否记录 `llm_trace.jsonl`。

### 2.2 Turn Output（内部）

- `assistant_text`: 本轮助手最终文本。
- `metadata.trace_id`: 本轮 trace 标识。
- `metadata.user_msg_uuid`: 本轮用户消息 UUID。

## 3. Transcript 行结构契约

- 文件：`<workspace>/transcript.jsonl`。
- 每行为 JSON 对象，最小字段：
  - `role`: `user` 或 `assistant`
  - `content`: 文本内容
  - `ts`: UTC ISO 时间
  - `uuid`: 消息唯一标识
- 扩展字段：
  - `reply_to`: assistant 行可指向 user 行 uuid
  - `trace_id`: 同一 turn 的关联标识
  - `heartbeat`: 仅心跳回合 user 行可出现，值为 `true`
  - `source`: assistant 来源（如 `chat`）

## 4. Tool Call Envelope 契约

- 工具声明统一来自 `workspace_init_tools.py` 构建的 registry。
- 工具执行统一通过 `execute_tool_call(...)`。
- 工具回填统一为 `role=tool` 消息，必须包含：
  - `tool_call_id`
  - `content`（工具返回文本）
- 非 heartbeat 回合才允许挂载工具。

## 5. Heartbeat Synthetic Turn 契约

- `heartbeat_turn=true` 时：
  - 输入文本强制替换为 `HEARTBEAT_SYNTHETIC_USER_TEXT`。
  - transcript 追加 user 行且可带 `heartbeat=true`。
  - 本轮不触发记忆管线更新。
  - 提示词构建需包含 heartbeat 语义段，且不改写既有 prompt 顺序。

## 6. 不可变约束（冻结）

- `orchestrator.run_turn` 是 assistant transcript 的单写入入口。
- `prompts.build_system_prompt` 的章节顺序不可变：
  - 固定安全基线
  - `AGENTS.md`（若存在）
  - `TOOLS.md`（若存在）
  - `HEARTBEAT.md`（若存在）
  - `IDENTITY.md`
  - `SOUL.md`
  - `context_mode` 条款
  - `USER.md`
  - intimate 模式下的日记/日总结/长期记忆
  - 输出与工具契约段
- runnable workspace 必选文件不可变：
  - `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`transcript.jsonl`
- 渠道接入必须经过统一 turn pipeline，禁止旁路直接写 transcript。

## 7. 兼容与迁移约束

- 旧入口迁移期允许 shim，但 shim 只能转发到统一 turn pipeline。
- 新增桥接（Telegram/voice/ws）必须先满足本文件不变量，再进入默认路径。

## 8. 验收标准（Phase 0）

- 契约文档落地，且被整合计划引用。
- 下列 gate 测试通过：
  - `test_transcript_for_llm_turn.py`
  - `test_heartbeat_schedule.py`
  - `test_workspace_bootstrap_loop.py`
