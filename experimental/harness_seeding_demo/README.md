# Harness seeding demo（试验设计）

本目录承载「Harness + 种子 vs 用户注入」对照试验的**唯一落点**。  
**约束**：不改动 `app/core/agentic_kernel/` 源码；仅沿用其架构与公开 API。

---

## 1. 借用的内核架构（只读依赖）

| 概念 | 代码位置（勿改） | 试验中的用途 |
|------|------------------|--------------|
| 单轮执行 | `app/core/agentic_kernel/companion/turn.py` → `run_turn` | 试验主循环每次调用的本体 |
| 会话与 LLM | `companion/manager.py` → `CompanionManager`, `CompanionSession`, `CompanionLLMClient` | 创建 session、共享模型配置 |
| 提示与上下文 | `companion/prompts.py`, `companion/models.py` → `PromptBundle`, `load_prompt_bundle` | 理解「种子」对应哪些 workspace 文件 |
| 可选 REPL 驱动 | `tools/inty_v2_repl/` | 人工演示时可不接新脚本，仍建议批跑用本目录脚本 |

试验层**只配置 workspace 初值 + 调用上述入口**，不 fork 推理核。

---

## 2. 目录规划（建议；尚未实现的占位）

```
experimental/harness_seeding_demo/
  README.md           # 本文件
  AGENTS.md           # 维护约定
  seeds/              # 多套 workspace **模板**（copy 后跑）
    baseline/         # 弱情绪先验
    empathic/         # 强共情先验（SOUL / TOOLS 等）
    functional/       # 偏任务拆解先验
    teammate_on/      # 可选：预填 USER.md 模拟团队注入
    teammate_off/     # 对照：USER.md 空或极短
  scripts/            # run_batch.py 等：复制 seed → 跑 N 轮 → 写结果
  scorer/             # 质量判定（规则或独立 LLM），**不属于** kernel
  results/            # .gitignore 建议忽略或大文件不进库
```

实现阶段再补 `requirements.txt`；依赖仅从 repo 根 `PYTHONPATH` 导入 kernel。

---

## 3. 种子（Teammate）在磁盘上的定义

不新增 Agent 类；**种子 = 初始化后的 workspace 文件集合**差异，例如：

- `SOUL.md`：共情 vs 结构化风格。
- `TOOLS.md`：与 kernel 工具契约对齐的「行为倾向」说明。
- `context.json`：`ContextMeta`（如 `context_mode`），影响 `load_prompt_bundle` 是否注入长记忆等。
- **团队注入**：实验组预先写好 `USER.md`（偏好、品味、禁忌）；对照组空白或极短。

固定 `IDENTITY.md` 或约定仅微小变动，避免与人设混淆。

---

## 4. 用户线（User ingestion）

- 每轮向 `run_turn(..., user_text=...)` 传入用户话语；权威 transcript 落在 workspace 的 `transcript.jsonl`（与现有 REPL 约定一致）。
- 对照公平性：同一**用户台本**（或同一字符预算的采样）用于所有种子；仅 workspace 初值不同。

---

## 5. 「自演化」在试验中的可观测性（不加 kernel 代码）

- 依赖既有 **memory 管线**与工具对工作区文档的改写（如 `USER.md` / `SOUL.md` / `MEMORY.md`），通过对比回合前后的文件快照或 hash 展示「形态变化」。
- 可选读取 **workspace 侧** `llm_trace.jsonl`（若使用 REPL 路径）做演示；不要求改 kernel。

---

## 6. 质量与效率指标（试验层实现）

- **实现位置**：本目录 `scorer/`，输入为「当前 assistant 回复 + 可选 transcript」，输出分数与是否越过目标线。
- **主指标**：达到目标「情感理解」分数所需的 **用户轮次数**。
- **辅指标**：用户台本 token 数或总字数（对比「团队预注开/关」时用户负担）。

---

## 7. 最小成功标准

- 单次演示能说明：在**同一 harness（同一 `run_turn` 链）**下，仅换 `seeds/*` 初值，**达标轮次**分布有明显差异。
- 全程无对 `app/core/agentic_kernel/` 的 diff。

---

## 8. 与仓库其它文档的关系

- Workspace 文件语义与加载顺序以 `tools/inty_v2_repl/AGENTS.md` 与 kernel 源码为准；本目录**不复制**长规范，只引用。
