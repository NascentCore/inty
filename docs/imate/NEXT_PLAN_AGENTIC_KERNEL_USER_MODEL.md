# 下一步计划：agentic kernel 差距与伴侣用户模型

本文档由 2026-05-09 相关讨论整理，供 iMate / agentic companion 方向排期用。

## 谈话结论（事实摘记）

- 已对照仓库根目录 `/AGENTS.md` 中 Agentic Companion 设计主轴，通读 `/app/core/agentic_kernel/` 实现与 `/app/core/agentic_kernel/AGENTS.md`、`/app/core/agentic_kernel/companion/AGENTS.md`、`/app/core/agentic_kernel/ISSUES.md`。
- 当前内核强项：`/app/core/agentic_kernel/companion/` 上的会话回合、分层记忆、异步工具链、图像类工具、陪伴心跳与定时提醒等；生产主入口在 `turn.py` 等 companion 模块，与 `runtime/TurnOrchestrator`、`bridges/experimental_bridge.py` 的通用骨架并存。
- 与产品愿景相比仍缺或偏薄：多媒介（短信/电话/语音/视频等）在本包内的一等公民抽象；**对「用户这一实体」的可交互建模**（原称「用户数字空间」易误解为空间拓扑而非对人的建模）；独立于主会话的「世界/环境」持续状态与事件引擎；用户侧多模态输入若存在需在契约层与内核对齐。
- 已记录技术债：部分模型将结构化输出放在 `reasoning` / `reasoning_details` 而非 `message.content`，工具后台路径仅读 `content`（见 `/app/core/agentic_kernel/companion/tool_background.py` 内 TODO）；`/app/core/agentic_kernel/ISSUES.md` 中偶发 LLM 无输出问题待闭环。
- 工程约定：`/app/core/agentic_kernel/__init__.py` 当前为空，与仓库「Python 包 `__init__.py` 宜有包级 docstring」的惯例不一致。

## 术语（对内文档与代码常量）

- 默认使用：**用户模型**（英：User Model）。
- 需与账号表 User、泛化「用户画像」区分时：**伴侣用户模型**（英：Companion User Model）。
- 避免继续使用易误解的「用户数字空间建模」作为该概念主名称。

## 下一步任务目标

- 在 `/app/core/agentic_kernel/companion/AGENTS.md` 或上层与 iMate 相关的架构文档中，写入上述术语约定并固定中英文对照。
- 定义 **伴侣用户模型** 的数据边界：字段集合、更新来源（用户显式 / 隐式信号如 `/app/schemas/implicit_signals.py`、记忆抽取等）、与 `USER.md`、transcript、记忆流水线的读写关系。
- 若新增持久化或 Pydantic schema：与 `companion_memory_document_versions`、`ContextMeta`（`/app/core/agentic_kernel/companion/models.py`）等现有真源对齐，命名与注释中统一使用「伴侣用户模型」以防与 ORM User 混淆。
- 按产品优先级推进 agentic kernel 缺口：多媒介通道抽象；用户侧多模态输入契约；独立于用户每轮输入的「世界/环境」状态与事件（若仍纳入本里程碑）。
- 实现或跟进 **companion-dual-envelope-reasoning-channel**：工具后台完成轮次从 `reasoning` / `reasoning_details` 与 `content` 统一解析双通道 envelope，与 `/app/core/agentic_kernel/companion/tool_bg_routing.py` 行为一致。
- 为 `/app/core/agentic_kernel/ISSUES.md` 中「无输出 LLM 调用」补充复现与降级策略（含观测字段与用户可见行为），关闭或降级为可监控的已知限制。
- 为 `/app/core/agentic_kernel/__init__.py` 补充包级 docstring，说明本包在系统中的角色（仅 docstring，不放功能性代码）。
- 评估是否将本计划中的「伴侣用户模型」拆成独立 FR 文档（`docs/FR_*.md`）并挂链接至本文档。

## 相关路径

- `/app/core/agentic_kernel/`
- `/app/core/agentic_kernel/ISSUES.md`
- `/docs/imate/DEV_PLAN.md`（其它条目如打电话、发短信可与此并行，本文档不替代该文件）
