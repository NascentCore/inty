# FR_BACKEND_ARCH_IMPROVEMENT_PLAN

<!-- CREATED_BY_AGENT -->

## 1. 文档目的

本文件整合以下 4 份历史文档（现已删除并收敛到本文件），形成一个统一的后端架构改进计划，供研发执行与跟踪：

- `app/todos/TODOS.md`
- `app/todos/TODOS_SCALABILITY.md`
- `app/api/README.md`
- `app/api/v1/endpoints/REPORT_API_ANALYSIS.md`

本计划聚焦 3 件事：

- 架构边界清晰化
- API 契约一致化
- 可扩展性与稳定性治理

## 2. 现状汇总

### 2.1 架构层面

- 已有分层目录，但跨层依赖规则与 CI 约束不完整。
- 依赖注入模式不统一，存在全局单例和隐式依赖。
- 错误模型未完全统一，存在多种错误返回风格并存。

### 2.2 API 层面

- 规范要求统一响应壳：`code/message/data`。
- 部分模块仍有兼容字段和历史路径，增加维护成本。
- Report 模块存在 `reason_codes` 与 `reason_ids` 双轨兼容。

### 2.3 可扩展性层面

- async 路径中仍有同步 I/O 和同步 DB 调用，存在事件循环阻塞风险。
- 聊天链路存在 N+1 和深分页性能问题。
- 并发控制、线程池、缓存、部署形态仍有系统性优化空间。

## 3. 改进目标与验收口径

### 3.1 目标

- 分层依赖可被静态检查，违规在 CI 阶段阻断。
- API 错误契约统一，客户端分支逻辑可预测。
- 关键链路无显著事件循环阻塞点，吞吐和尾延迟稳定。

### 3.2 验收口径

- 架构规则：存在可执行检查脚本，并接入 CI。
- API 契约：核心 endpoint 响应结构一致，文档与实现一致。
- 性能与稳定性：针对聊天、生图、语音链路有可复现的压测或回归结果。

## 4. 执行路线图

## Phase P0 - 必须优先完成

### A. 架构分层与边界

- 明确 `api/schemas/services/models/utils/middleware/external_services` 职责。
- 建立跨层依赖禁止清单。
- 接入 CI 检查，阻断新增架构违规。

完成情况（2026-04-02）：

- 状态：DONE
- 已交付：`backend/docs/ARCH_LAYER_BOUNDARY_RULES.md`
- 已交付：`scripts/check_layer_dependencies.py`
- 已接入：`.github/workflows/ci_backend.yaml` 新增 `Check architecture layer boundaries`
- 验证：
  - `.venv/bin/python scripts/check_layer_dependencies.py`（通过）
  - 人工注入违规样例后再次运行脚本（失败并输出违规）

交付物：

- 架构边界说明文档
- 依赖检查脚本和 CI 任务

### B. 依赖注入统一

- service/repository 统一通过 `Depends` 暴露和注入。
- 清理全局单例与隐式依赖入口。

完成情况（2026-04-02）：

- 状态：DONE（第一批）
- 已交付：`app/api/deps.py` 新增 `get_subscription_service`、`get_voice_service`
- 已交付：`app/api/v1/endpoints/chat.py` 将聊天主链路与相关接口改为通过 `Depends` 注入 `SubscriptionService`/`VoiceService`
- 已交付：`app/api/v1/endpoints/chats.py` 将语音与聊天设置相关接口改为通过 `Depends` 注入 `SubscriptionService`/`VoiceService`
- 已交付：`tests/app/api/v1/endpoints/test_chat.py`、`tests/app/api/v1/endpoints/test_chats.py` 适配依赖注入路径并保持回归覆盖
- 验证：
  - `.venv/bin/pytest tests/app/api/v1/endpoints/test_chat.py -k "test_v1_chat_completions_guest_requires_login or test_v1_chat_completions_prefers_chat_settings_voice_id_for_autoplay or test_v1_chat_generate_image_wraps_business_error or test_v1_chat_generate_music_success" -q`（通过）
  - `.venv/bin/pytest tests/app/api/v1/endpoints/test_chats.py -k "test_generate_message_voice_guest_login_required or test_generate_message_voice_success_includes_gcs_urls or test_update_chat_settings_requires_subscription" -q`（通过）

交付物：

- DI 使用规范
- 核心路由模块改造 PR

### C. 错误模型统一

- 统一错误响应模型，例如 `{code, message, details, request_id}`。
- 建立 HTTP status 与业务错误码映射规范。
- 日志中补齐请求关联标识，便于追踪。

交付物：

- 统一错误处理中间件或公共封装
- 错误码映射表

### D. 可观测性基础

- 接入 Trace/Metrics/Logs 方案。
- 打通 `x-request-id` 全链路传递。

交付物：

- 指标面板最小集
- 端到端请求追踪样例

### E. 数据迁移治理

- 统一 Alembic 命名和审查流程。
- 增加迁移自动校验，减少不可逆风险。

交付物：

- 迁移审查 checklist
- CI 迁移校验步骤

### F. 契约与集成测试

- 按 API 规范补齐 FastAPI TestClient 集成测试。
- 与 Android 端契约打通，覆盖核心 endpoint。

交付物：

- 关键 endpoint 契约测试
- E2E 回归基线

## Phase P1 - 高优先改造

### A. 事件循环阻塞治理

- `chat_history_service` 同步调用统一包装为 `asyncio.to_thread` 或等价方案。
- GCS 同步 SDK 调用统一改为异步包装或后台执行。
- 语音链路中的同步 I/O 从请求主链路剥离。

验收：

- 关键 async 路径不再直接执行同步网络 I/O。
- 聊天主链路在压测下尾延迟可控。

### B. 查询与分页优化

- 聊天列表 N+1 查询治理。
- 深分页从 OFFSET 向 cursor 方案演进。
- 对热点 JSON 解析路径进行索引/缓存优化。

验收：

- 查询次数和慢查询指标下降。
- 深分页响应时间随页深增长更平滑。

### C. 缓存与并发控制

- 统一 Redis 键命名、TTL、失效策略。
- 增加防击穿/雪崩策略和热点监控。
- 重构 Agent 线程池和并发上限控制。

验收：

- 缓存命中率与错误率可观测。
- 高并发下线程数和队列长度受控。

### D. API 合同稳定性

- 统一分页结构和确定性排序。
- 明确兼容字段生命周期，推进下线计划。

验收：

- 文档和实现一致。
- 历史兼容字段有明确删除窗口与迁移通知。

## Phase P2 - 中优先与长期项

- 后台任务体系标准化（队列选型、状态表、可视化、告警）。
- 流式接口协议统一（心跳、重连、鉴权、限流）。
- 资源与媒体治理（CDN/GCS 路径归一化、配额与限速）。
- RAI 与安全策略（输入校验、内容过滤、审计）。
- CI/CD 完善（类型检查、回滚手册、变更说明自动化）。

## 5. 专项计划 - Report API 兼容债务收敛

来源：历史文档 `app/api/v1/endpoints/REPORT_API_ANALYSIS.md`（已整合到本文件）

### 5.1 当前状态

- 请求侧推荐 `reason_codes`，但仍兼容 `reason_ids`。
- 数据层仍保留 `reason_ids` 历史字段。

### 5.2 收敛策略

- 第一步：继续读兼容，写入以 `reason_codes` 为准。
- 第二步：客户端和服务端文档统一声明 `reason_ids` 废弃。
- 第三步：完成数据回填后移除 `reason_ids` 读写路径。

### 5.3 验收

- 新请求仅依赖 `reason_codes`。
- 相关测试覆盖旧数据读取与新数据写入。
- API 文档不再把 `reason_ids` 作为推荐输入。

## 6. 实施顺序建议

建议按以下顺序推进，降低耦合风险：

1. 错误契约和依赖注入统一（影响面大，需先稳定接口行为）
2. 事件循环阻塞治理（直接影响稳定性和性能）
3. 查询优化与缓存治理（提升吞吐）
4. Report 等模块兼容债务清理（降低长期维护成本）
5. 后台任务和流式协议标准化（中长期演进）

## 7. 交付管理

每个阶段的任务都应包含：

- 设计说明：目标、范围、非目标
- 代码改动：最小可合并单元
- 测试证据：集成测试或 E2E 结果
- 文档更新：API 文档、迁移说明、测试步骤

推荐将关键测试步骤沉淀到 `tests/docs/`，便于回归和交接。

## 8. 里程碑跟踪模板

| Workstream | Owner | Status | Key Deliverable | Test Evidence |
| --- | --- | --- | --- | --- |
| Layer boundaries and CI rules | Cursor Agent | DONE | `backend/docs/ARCH_LAYER_BOUNDARY_RULES.md` + `scripts/check_layer_dependencies.py` + CI gate | `.venv/bin/python scripts/check_layer_dependencies.py` + injected violation check |
| DI unification | Cursor Agent | DONE (batch 1) | `app/api/deps.py` + `app/api/v1/endpoints/chat.py` + `app/api/v1/endpoints/chats.py` Depends 注入落地 | targeted `test_chat.py` + `test_chats.py` regression |
| Error model unification | TBD | TODO | Unified error envelope | API snapshot tests |
| Async blocking fixes | TBD | TODO | to_thread/async wrappers | Load test metrics |
| Query and pagination optimization | TBD | TODO | N+1 and cursor migration | Query count + latency |
| Report compatibility cleanup | TBD | TODO | reason_codes-only write path | Report API tests |

## 9. 历史来源文档（已整合并删除）

- `app/todos/TODOS.md`
- `app/todos/TODOS_SCALABILITY.md`
- `app/api/README.md`
- `app/api/v1/endpoints/REPORT_API_ANALYSIS.md`
