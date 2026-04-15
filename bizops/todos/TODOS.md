## 仓库任务文档索引

模型选型考虑参数指标：延时、成本、质量（按重要性递减顺序排列）

文本模型：Gemini qwen claude openai
生图：Gemini qwen/fal.ai
tts：elevenlabs Gemini fal.ai/开源模型

以下列出了当前仓库内所有记录待办/任务信息的 Markdown 文档，方便团队快速定位具体负责范围的 backlog。

- [`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](../../docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md)：后端（FastAPI）架构与 API 治理统一改进计划，整合分层、依赖注入、错误模型、可扩展性与 Report 兼容治理。
- [`android_app/TODOS.md`](../android_app/TODOS.md)：Android 客户端的架构级待办，涵盖网络栈统一、OpenAPI SDK 接入、依赖注入与 UI 基线等工作。
- [`android_app/TODOS_CLEANUP_WARNINGS.md`](../android_app/TODOS_CLEANUP_WARNINGS.md)：Android 端单元测试阶段产出的编译/弃用 API 警告清单与对应修复计划。
- [`android_app/TODOS_INTY_SDK.md`](../android_app/TODOS_INTY_SDK.md)：Inty Kotlin SDK 迁移任务，列出尚未由生成 SDK 覆盖的接口以及迁移优先级。
- [`bizops/TODOS.md`](../bizops/TODOS.md)：商业运营推进事项，追踪卸载率等核心指标与数据看板搭建任务。
- [`bizops/todos/图片超分.md`](./图片超分.md)：通过 Firebase 事件数据评估图片超分功能点击与转化，并决定是否继续开发。
- [`docs/TODOS.md`](docs/TODOS.md)：跨端 API 与架构改进路线，包括 OpenAPI 真源、鉴权统一、合同测试等跨团队协作事项。
- [`evaluation/TODOS.md`](../evaluation/TODOS.md)：评测前端需要完成的目录规范、SDK 接入、可观测性与测试策略任务。
- [`.github/workflows/KOTLIN_TODOS.md`](../.github/workflows/KOTLIN_TODOS.md)：CI 中 Kotlin 工作流的改进事项，如模块映射自动化与 Gradle 缓存策略优化。

> 若有新的任务型 Markdown 文档，请同步将链接与一句话简介追加到本索引中，保持仓库任务视图的一致性。
