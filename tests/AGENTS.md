# `tests/`：后端与契约的验证策略

**一句话**：这里偏 **「黑盒式功能测试」**——在真实或接近真实的栈上走通关键路径；**不写细碎单元测试**，除非人类明确要求补窄回归。

## 读者

- 为 API、伴侣链路或跨服务契约加 **端到端保障** 的工程师。

## 核心哲学

- **真栈优先**：倾向 **真实数据库 + 本地起服务**；外部世界用仓库提供的 **fake 服务** 替身，而不是到处 mock SQLAlchemy。
- **Companion MemoryStore 注册表**：凡调用 `get_memory_store(..., dsn=...)` 且依赖 ORM 持久化的用例，假定仓库根 `config.yaml` 的 `database.url` 非空且 Postgres 可用（与 `companion_memory_registry_dsn` 辅助一致）；仅需内存行为时用 `MemoryStore(..., repository=None)`，勿传空 `dsn` 走注册表。
- **monkeypatch 例外**：极少数历史 WebSocket 测试允许隔离鉴权与模型调用；**新契约关键路径** 优先 **真服务 + token**（与 `app/AGENTS.md` 精神一致）。
- **够不着就跳过**：当默认 `localhost:8000` 不可达时，HTTP 集成夹具会 **跳过** 而非让整个 `pytest` 红一片——鼓励本地开发「不启服也能跑大部分」。

## 怎么跑（指向操作而非背脚本）

- **常规**：准备 Postgres + 测试配置 + 启动 inty 后端，再跑带 `not noci` 标记的 pytest 子集；具体命令以 `tests/docs` 与 CI 配置为真源。
- **真 LLM / 真 WS 的选做实验**：通过环境变量闸门开启；详见 `tests/docs` 下对应步骤文档与 **仓库技能** `inty-backend-ci-local` / `inty-server-module-verify` 指引。

## 与客户端协同时的防遗漏

- **契约单一真源**：枚举、排序参数、错误码以后端 schema 为准；改名改值要 **多端同 PR 或明确版本门**。
- **测「路径存在」**：新 query 组合、新 sort 等要在测试中 **至少命中一次 200**，避免 silently 422。
- **别让失败看起来像空数据**：客户端与测试都应能区分 **错误态与真空态**。
