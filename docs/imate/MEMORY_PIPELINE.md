# Companion 记忆管线综述（document MemoryStore 路径）

本文描述 **当前已实现** 的 agentic companion 分层记忆：`app/core/agentic_kernel/companion/memory_pipeline.py` 写入，`models.load_prompt_bundle` 读出，`prompts.build_system_messages` 注入 LLM。与 `docs/imate/FR_AGENTIC_MEMORY_STORE.md` 所述 **未来向量 LTM** 正交；本节不涉及 legacy 主站 `memory` 表。

---

## 一句话

Companion 在 MemoryStore 里维护三层 Markdown：**情景 episodic**（`memory/daily/<日期>.md`）按轮追加流水，**gist**（`memory/<日期>.md`）做当日摘要，**语义 semantic**（`MEMORY.md`）做跨日整合；回合末按间隔触发策展模型重写 gist / semantic（并可顺带策展 USER / SOUL），亲密类 experience profile 下三层装入 system prompt。

---

## 一段话

每轮用户可见对话结束后，管线向当日 episodic 文件 **追加一行**带时间戳的 user/assistant 裁剪摘要。达到配置的间隔时，用当日 episodic 全文、上一轮 gist 文件与 **最新一轮 turn** 调用 LLM 重写 **gist** 单日结构化纪要（`memory/<日期>.md`）。再在同管线逻辑下按间隔将当日 gist 片段、当前 `MEMORY.md` 与最新 turn 交给 **memory curator**，输出更新后的 **语义** 长期正文。并行可选：按间隔策展 `USER.md`、`SOUL.md`（SOUL 可要求本轮出现「基调 / 边界」类信号才触发）。**Experience profile** 为 `intimate` 或 `emotional_companion` 时，`load_prompt_bundle` 读取 episodic / gist 日程路径并将 `MEMORY.md` 注入 `PromptBundle`；否则不读日程且语义注入留空。`build_system_messages` 将三层分别以固定标题注入（见 `app/core/agentic_kernel/companion/memory_taxonomy.py`），标题中带路径与中英术语，便于对齐概念与代码。

---

## Bullet 要点

- **存储语义**：路径均在 **MemoryStore**（companion 工作区持久化语义信息集合），逻辑 POSIX 相对路径；生产环境下权威往往在 PostgreSQL `companion_memory_document_versions`，不是用户设备文件夹。
- **L1 情景记忆 episodic**：`memory/daily/{date}.md`；`_append_diary` 每轮追加。
- **L2 gist 单日摘要**：`memory/{date}.md`；`_rewrite_day_summary_md`；受 `MemoryPipelineConfig.day_summary_every_n_turns`、`day_summary_disabled` 控制。
- **L3 语义记忆 semantic**：`MEMORY.md`；`_rewrite_memory_md`；受 `memory_update_every_n_turns` 等控制；策展 system prompt 约束事件日志 / 稳定事实等（见 `memory_pipeline.py`）。
- **USER / SOUL 策展**：同一管线内可选间隔更新；SOUL 可与「根本性互动信号」门禁联动（`soul_require_fundamental_signal`）。
- **装入模型**：`models.load_prompt_bundle` + `experience_profile_injects_private_memory`；system 块标题常量 **`memory_taxonomy.py`**，与 `companion/README.md` 表格一致。
- **切片枚举关系**：`prompt_slices.PromptSliceId.MEMORY` 仅对应根目录 `MEMORY.md`（语义层）；episodic / gist 为 **层级路径**，不由该枚举映射。
- **编排入口**：回合结束后 `memory_update_after_turn` / `schedule_memory_update_after_turn`（见 `memory_pipeline.py`、`turn.py`）；具体阈值与禁用开关见 `MemoryPipelineConfig`、`CompanionManager` 传入配置。

---

## 代码索引

| 主题 | 路径 |
|------|------|
| 管线实现 | `app/core/agentic_kernel/companion/memory_pipeline.py` |
| 读出与 bundle | `app/core/agentic_kernel/companion/models.py` (`load_prompt_bundle`) |
| System 注入标题 | `app/core/agentic_kernel/companion/memory_taxonomy.py` |
| System 组装 | `app/core/agentic_kernel/companion/prompts/system_messages.py` (`build_system_messages`) |
| 路径 kind 映射 | `app/core/agentic_kernel/companion/memory_store_document_mapping.py` |
| 概述文档 | `app/core/agentic_kernel/companion/README.md` |
