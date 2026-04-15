# 后端 Q1 工作计划（2026.01-2026.03）

<!-- CREATED_BY_AGENT -->

> 本文档基于 2026 年 1 月团队会议讨论内容整理，作为后端未来 3 个月的工作指引；下方「执行进度」随代码库状态滚动更新。

## 执行进度（截至 2026-03-24）

以下对照各阶段计划，依据仓库当前实现梳理；更新本节后请同步修改日期与条目状态。

### 第一阶段：数据分析与可观测性

| 子项 | 状态 | 说明 |
| ---- | ---- | ---- |
| 1.1 扩展用户分析能力（单用户画像、漏斗、留存归因等 API） | **部分完成** | [`UserAnalyticsService`](../app/services/user_analytics_service.py) 与 Ops 侧评测/分析接口（[`backend/ops/api/v1/evaluation.py`](../backend/ops/api/v1/evaluation.py)）已承载大量聚合统计；[`user_analytics_report`](../app/models/user_analytics_report.py) 表与 [`user_analytics_report_service`](../app/services/user_analytics_report_service.py) 支持日报/周报预计算与推送调度任务。计划中明确列出的**单用户行为画像 API、功能漏斗、留存归因（如 D7 对比）**等需在服务层与接口上逐项对照补全或文档化。 |
| 1.1 多数据源统一聚合（MetricsCollector 架构图） | **未落地** | Firebase / Play Console / Cloud Console 等与 PG 的统一采集层尚未按该架构实现。 |
| 1.2 OpenTelemetry 接入生产 | **未接入主应用** | 仅有实验性示例：[`experimental/fastapi_otel/main.py`](../experimental/fastapi_otel/main.py)。主 FastAPI 进程未挂载 OTel。 |

### 第二阶段：零停机部署与稳定性

| 子项 | 状态 | 说明 |
| ---- | ---- | ---- |
| 2.1 零停机 / 滚动或蓝绿部署 | **未完成** | [`.github/workflows/build_and_deploy_backend.yml`](../.github/workflows/build_and_deploy_backend.yml) 仍为 `docker stop` / `docker rm` 后单容器拉起；[`backend/inty/start.sh`](../backend/inty/start.sh) 仍为单进程 `uvicorn`，未采用计划中的 gunicorn 多 worker + 流量切换方案。 |
| 2.2 事件循环阻塞、同步 DB/GCS 等 | **部分推进** | 多处已使用 `asyncio.to_thread`（如聊天消息分页、记忆投递、GCS、TTS 等）。[`chat_history_service`](../app/services/chat_history_service.py) 仍在 [`chat_service`](../app/services/chat_service.py)、[`agent`](../app/core/agent/agent.py) 等路径上同步调用，需继续按 [`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](./completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md) 收敛。 |

### 第三阶段：商业化功能支撑

| 子项 | 状态 | 说明 |
| ---- | ---- | ---- |
| 3.1 订阅价值量化、转化漏斗、AB 实验 | **待对齐** | [`subscription_service`](../app/services/subscription_service.py) 等需与产品确认是否已有等价能力；计划中的专项 API/框架未见完整落地描述。 |
| 3.2 广告系统基础 | **待对齐** | 广告位配置、展示与收益统计类 API 需在 `app/api` 与 schema 层逐项核对是否已存在或仍属规划。 |

### 第四阶段：产品功能

| 子项 | 状态 | 说明 |
| ---- | ---- | ---- |
| 4.1 记忆系统 | **部分完成（形态与计划不完全一致）** | 已有 [`Memory`](../app/models/memory.py) 模型、抽取与节日/日常记忆链路、角色详情中的 `festival_memories` / `daily_memories` 等（见 [`memory_service`](../app/services/memory_service.py)、[`app/schemas/agent.py`](../app/schemas/agent.py)）。计划中 **`GET/POST/PUT/DELETE /api/v1/memories` 用户侧 CRUD** 若仍需，应单独排期并与 Android 契约同步。 |
| 4.2 亲密度系统 | **未实现** | 未见独立 `intimacy` 表与后端服务。 |
| 4.3 成就系统 | **未实现** | 未见 `achievements` / `user_achievements` 表与触发、发奖服务。 |

### 与 § 优先级排序的对应关系（快照）

- **P0 单用户分析 / 功能归因**：有分析服务与报表基础，**与计划条目的 1:1 完成度需产品/研发共同勾选**。
- **P0 零停机部署**：**未完成**。
- **P1 OpenTelemetry**：**未完成（主应用）**。
- **P1 事件循环与扩展性**：**进行中**。
- **P1 记忆系统**：**自动记忆与端上展示相关能力已有**；**用户可编辑 CRUD API 按原计划仍缺**。
- **P2 订阅分析、亲密度、成就**：**基本未动或待确认**。

---

## 背景分析

根据会议讨论，后端面临以下核心挑战：

1. **数据孤岛问题**：数据散落在 Firebase、Google Play Console、Cloud Console、DB，缺乏统一分析能力
2. **发布中断问题**：后端发布时 `docker stop/rm` 导致服务短暂不可用
3. **商业化支撑不足**：付费体系不完整，缺少数据依据
4. **产品功能缺口**：记忆系统、亲密度、成就系统等功能需要后端支持

结合现有技术债务（[`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](./completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md)），制定以下分阶段计划。

---

## 第一阶段：数据分析与可观测性（1-2 月）

### 1.1 统一数据分析平台

**目标**：解决"无法分析单一用户使用情况"和"功能效果无法量化"问题

- 扩展 [`app/services/user_analytics_service.py`](../app/services/user_analytics_service.py) 现有能力：

  - 单用户行为画像 API：聊天次数、生图次数、语音通话次数、耗时分布
  - 功能漏斗分析 API：注册 → 首次聊天 → 首次生图 → 首次语音 → 付费转化
  - 留存归因 API：新功能上线前后对比（如语音通话功能对 D7 留存的提升）

- 新增数据聚合服务，整合多数据源：

```
数据源                          后端聚合层                    输出
┌─────────────────┐      ┌────────────────────┐      ┌─────────────────┐
│ Firebase        │──┐   │                    │      │                 │
│ Analytics       │  │   │  MetricsCollector  │──┐   │  Evaluation     │
├─────────────────┤  ├──▶│                    │  │   │  看板           │
│ Google Play     │  │   ├────────────────────┤  ├──▶│                 │
│ Console         │──┤   │                    │  │   ├─────────────────┤
├─────────────────┤  │   │  UserAnalytics     │──┤   │                 │
│ Cloud Console   │──┤   │  Service           │  │   │  告警系统       │
├─────────────────┤  │   ├────────────────────┤  │   │                 │
│ PostgreSQL      │──┘   │  数据仓库/BigQuery │──┘   └─────────────────┘
└─────────────────┘      └────────────────────┘
```

### 1.2 可观测性建设

**目标**：解决"不知道系统性能瓶颈在哪"的问题

- 接入 OpenTelemetry（已在 [`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](./completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md) P0 列表）
- 核心指标埋点：
  - 请求 P50/P95/P99 延迟
  - LLM 调用延迟（已有 `/user-analytics/llm-latency` 基础）
  - 事件循环阻塞时间
  - 数据库连接池使用率

---

## 第二阶段：零停机部署与稳定性（2 月）

### 2.1 零停机部署

**目标**：解决"后端发布导致服务中断"问题

当前 [`build_and_deploy_backend.yml`](../.github/workflows/build_and_deploy_backend.yml) 使用 `docker stop/rm/run` 模式，改为滚动更新：

- **方案 A（推荐）**：启用多 worker 模式 + 健康检查

  - 修改 [`backend/inty/start.sh`](../backend/inty/start.sh) 使用 `gunicorn + uvicorn workers`
  - nginx 配置健康检查，新容器就绪后再切流量

- **方案 B**：Blue-Green 部署
  - 两个容器并行，切换 nginx upstream

### 2.2 性能优化（P0 级阻塞问题）

- 修复事件循环阻塞（[`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](./completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md) P0）：
  - `chat_history_service` 同步 DB 调用 → `asyncio.to_thread()`
  - GCS 同步 SDK → 异步包装
- N+1 查询优化：`get_chats()` 批量查询重构

---

## 第三阶段：商业化功能支撑（2-3 月）

### 3.1 订阅体系完善

- 扩展 [`app/services/subscription_service.py`](../app/services/subscription_service.py)：
  - 订阅价值量化 API：订阅用户 vs 非订阅用户的功能使用对比
  - 订阅转化漏斗数据
  - AB 测试框架支持（价格、套餐、权益实验）

### 3.2 广告系统基础

- 广告位配置 API
- 广告展示记录与收益统计

---

## 第四阶段：产品功能（3 月）

### 4.1 记忆系统（Memory System）

**目标**：支持用户"浏览/增删改 AI 记忆"

**数据模型**：

| 字段        | 类型     | 说明                             |
| ----------- | -------- | -------------------------------- |
| id          | UUID     | 主键                             |
| user_id     | String   | 用户 ID（外键）                  |
| agent_id    | String   | 角色 ID（外键）                  |
| content     | Text     | 记忆内容                         |
| memory_type | Enum     | 记忆类型（用户偏好/事件/关系等） |
| is_active   | Boolean  | 是否生效                         |
| created_at  | DateTime | 创建时间                         |
| updated_at  | DateTime | 更新时间                         |

**API 设计**：

- `GET /api/v1/memories` - 列出用户与角色的记忆
- `POST /api/v1/memories` - 手动添加记忆
- `PUT /api/v1/memories/{id}` - 编辑记忆
- `DELETE /api/v1/memories/{id}` - 删除记忆

**核心能力**：聊天时自动提取和使用记忆

### 4.2 亲密度系统

- 新增 `intimacy` 表：用户-角色亲密度值
- 亲密度增长规则：聊天、送礼、任务完成
- 亲密度等级与解锁内容关联

### 4.3 成就系统

- 新增 `achievements` 和 `user_achievements` 表
- 成就触发条件检测服务
- 奖励发放机制

---

## 优先级排序

| 优先级 | 工作项             | 预估工时 | 产出价值                           |
| ------ | ------------------ | -------- | ---------------------------------- |
| P0     | 单用户行为分析 API | 3-4 天   | 解决"无法分析用户使用情况"核心痛点 |
| P0     | 功能效果归因 API   | 3-4 天   | 为产品决策提供数据依据             |
| P0     | 零停机部署         | 2-3 天   | 消除发布时用户体验损失             |
| P1     | OpenTelemetry 接入 | 2-3 天   | 系统可观测性基础                   |
| P1     | 事件循环阻塞修复   | 3-4 天   | 提升系统吞吐量                     |
| P1     | 记忆系统           | 5-7 天   | 产品差异化核心功能                 |
| P2     | 订阅数据分析       | 3-4 天   | 商业化决策支撑                     |
| P2     | 亲密度系统         | 4-5 天   | 提升用户留存                       |
| P2     | 成就系统           | 4-5 天   | 提升用户参与度                     |

---

## 与前端协同点

1. **数据分析**：与 evaluation 前端对接新的分析 API，扩展看板
2. **记忆系统**：与 Android 端协同定义 API 契约，支持记忆展示与编辑 UI
3. **亲密度/成就**：前端需要展示进度、等级、奖励等 UI 元素

---

## 里程碑时间线

```
1 月                    2 月                    3 月
├─────────────────────┼─────────────────────┼─────────────────────┤
│ 数据分析 API         │ 零停机部署          │ 记忆系统            │
│ 可观测性接入          │性能优化            │ 亲密度系统          │
│                     │ 订阅分析            │ 成就系统            │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

---

## 建议的下一步行动

1. 确认本计划的优先级排序是否符合团队预期
2. 与产品确认记忆、亲密度、成就的具体规则定义
3. 与前端同步 API 设计，建立契约测试

---

## 相关文档

- [`docs/completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md`](./completed/FR_BACKEND_ARCH_IMPROVEMENT_PLAN.md) - 后端架构改进统一计划
- [`devops/RELEASE.md`](../devops/RELEASE.md) - 发布流程
- [`app/services/user_analytics_service.py`](../app/services/user_analytics_service.py) - 现有用户分析服务
