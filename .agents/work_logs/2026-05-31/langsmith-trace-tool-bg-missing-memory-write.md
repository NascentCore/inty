# LangSmith trace 019e77b1：tool_background 未调用 memory_store_write_document

**一句话**：用户明确要求停用「抓到」等避讳词时，tool_background 只 read/list 约定文档却在收尾 JSON 里口头「除名」，未执行 `memory_store_write_document`。

## 分析要点

- Trace `019e77b1-0627-7171-b653-43e8968a8454`（`inty-backend-dev`）：`agentic_companion_chat` 快路径已回复；`tool_background` 8 轮 LLM，工具序列为 `read(context.json)` → `list_paths`×3 → `read(daily)` → `read(USER.md)` → `read(STYLE.md)`，无 write。
- 用户末句：`不要老是说"抓到"`——与档案中 `2026-05-29 别老用捏` 同类，system[15] 条款 (2) 要求 read 后 write。
- 根因：模型将 `output_to_user:false` + 收尾文案「以后这个词在资料阁除名」误判为已完成静默持久化；`STYLE.md`「谨慎、稳步调整」与 post-turn memory pipeline 语义叠加，抑制即时 write。

## 已做修复

- 新增 `tool_bg_memory_write_gap.py`：检测「用户持久偏好 + 已 read 约定稿 + 无 write」时注入一次 system nudge 并续跑 tool loop（`tool_background.py`）。
- 收紧 `system_messages.py` 与 `tool_bg_routing.py` 中关于避讳词与「禁止口头持久化」的说明。
- 归档 trace：`.inty/langsmith_traces/019e77b1-0627-7171-b653-43e8968a8454.json`（下载需 dev `langchain_api_key`，非 test config）。

## 后续待办

- 在真实 dev 环境复现同一用户句，确认 nudge 后 LangSmith 出现 `memory_store_write_document`。
- 若仍漏写，考虑在 memory_pipeline 慢路径对 USER/STYLE 做确定性 append（与 LLM write 去重）。
