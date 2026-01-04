# 运营平台现状与未来方案

*CREATED_BY_AGENT*

## 当前运营平台架构

### 1. 现有组件

#### 1.1 IntyEval（独立运营应用）

**位置**：`eval_app/`

**状态**：仍在构建中

**架构**：

- **后端**：独立的 FastAPI 应用（端口 8001）
- **前端**：React/TypeScript 应用（位于 `evaluation/`）
- **数据库**：与主应用共享同一数据库
- **服务层**：直接调用 `app/services/` 中的服务类

**功能范围**：

- ✅ 评测会话管理（`/api/v1/evaluation/*`）
- ✅ 评测模板管理
- ✅ 用户数据分析
- ✅ 智能体管理（评测专用）
- ✅ 共享端点：Agent、Chat、User、Images、TTS、Character Themes

**问题**：

- ⚠️ 与主应用混合部署，存在安全风险
- ⚠️ 影响业务逻辑和部署复杂度
- ⚠️ 直接访问生产数据库，可能造成性能压力

#### 1.2 Evaluation 前端

**位置**：`evaluation/`

**技术栈**：React + TypeScript + Vite

**当前部署方式**：

- 构建后拷贝到 `app/static/evaluation/`
- 由主应用后端在 `/evaluation` 路由提供访问
- 或通过独立开发服务器（HMR）在 `:3000` 端口运行

**功能页面**：

- `AgentManagePage.tsx` - 智能体管理
- `CharacterThemeManagePage.tsx` - 角色主题管理
- `EvaluationPage.tsx` - 评测页面
- `EvaluationHistoryPage.tsx` - 评测历史
- `UserAnalyticsPage.tsx` - 用户数据分析
- `UserDailyMessagesPage.tsx` - 用户每日消息统计
- `ChatPage.tsx` - 聊天页面
- `VoiceChatPage.tsx` - 语音聊天页面
- `GeneratedImagesPage.tsx` - 生成图片管理
- `ReportFeedbackPage.tsx` - 报告反馈
- `SettingsPage.tsx` - 设置页面

### 2. AI 角色创建与发布流程

#### 2.1 角色状态管理

**状态枚举**（`AgentStatus`）：

- `PENDING` - 待审核（默认状态）
- `APPROVED` - 已审核通过
- `REJECTED` - 已拒绝

**可见性**（`AgentVisibility`）：

- `PUBLIC` - 公开（默认）
- `PRIVATE` - 私有

#### 2.2 当前创建流程

1. **用户创建角色**：
   - 通过 `/api/v1/ai/agents` POST 接口创建
   - 默认状态为 `PENDING`
   - 默认可见性为 `PUBLIC`
   - 受订阅限制（普通用户最多 6 个）

2. **角色审核**：
   - 目前**没有明确的审核流程**
   - 状态字段存在但缺少审核界面和工作流
   - 需要手动在数据库中更新状态

3. **角色发布**：
   - 只有 `status = APPROVED` 且 `visibility = PUBLIC` 的角色才会出现在推荐列表
   - 推荐接口：`/api/v1/ai/agents/recommend`
   - 过滤条件：`status = APPROVED` 且 `visibility = PUBLIC`

#### 2.3 当前问题

- ❌ **缺少审核界面**：无法在运营平台中审核角色
- ❌ **缺少发布工作流**：没有明确的发布流程
- ❌ **状态管理混乱**：状态更新需要手动操作数据库
- ❌ **缺少版本管理**：角色更新后没有版本控制
- ❌ **缺少发布历史**：无法追踪角色的发布历史

### 3. 数据库访问现状

#### 3.1 当前架构

```
运营平台 (eval_app)
    ↓ [直接连接]
生产数据库 (Cloud SQL)
    ↓ [共享连接池]
主应用 (app)
```

**问题**：

- ⚠️ 运营查询影响生产数据库性能
- ⚠️ 连接池可能被耗尽
- ⚠️ 无法隔离运营和分析查询

#### 3.2 数据分离方案

详见：`bizops/OPS_PLATFORM_DB.md`

**推荐方案**：

- **BigQuery**：用于分析查询、报表生成
- **Read Replica**：用于需要实时性的查询
- **混合方案**：结合两者优势

## 未来方案：分离的运营平台

### 目标

1. **完全分离**：运营平台与主应用完全独立
2. **角色管理**：支持产品经理创建、审核、发布 AI 角色
3. **工作流**：建立完整的角色生命周期管理
4. **数据隔离**：运营查询不影响生产数据库
5. **安全性**：独立的认证和授权机制

### 架构设计

#### 1. 应用架构

```text
┌─────────────────────────────────────────────────────────┐
│                   运营平台 (Ops Platform)                 │
├─────────────────────────────────────────────────────────┤
│  前端 (React/TypeScript)                                 │
│  - 角色管理界面                                          │
│  - 审核工作流                                            │
│  - 数据分析仪表板                                        │
│  - 评测管理                                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  后端 (FastAPI - eval_app/)                              │
│  - 角色创建/更新 API                                     │
│  - 审核工作流 API                                        │
│  - 发布管理 API                                          │
│  - 数据分析 API                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────┐                    ┌──────────────┐
│  BigQuery    │                    │ Read Replica │
│  (分析查询)   │                    │  (实时查询)   │
└──────────────┘                    └──────────────┘
        ↑                                   ↑
        └─────────────────┬─────────────────┘
                          ↓
              ┌───────────────────────┐
              │  生产数据库 (Cloud SQL) │
              │  [Datastream CDC]     │
              └───────────────────────┘
```

#### 2. 角色生命周期管理

```text
创建 (Create)
    ↓
待审核 (PENDING)
    ↓
审核中 (REVIEWING) ← 新增状态
    ↓
    ├─→ 审核通过 (APPROVED)
    │       ↓
    │   发布 (PUBLISHED) ← 新增状态
    │       ↓
    │   上线 (LIVE) ← 新增状态
    │
    └─→ 审核拒绝 (REJECTED)
            ↓
        修改后重新提交
```

**新增状态**：

- `REVIEWING` - 审核中（分配给审核人员）
- `PUBLISHED` - 已发布（审核通过，准备上线）
- `LIVE` - 已上线（对用户可见）
- `ARCHIVED` - 已归档（下线但保留历史）

#### 3. 功能模块设计

##### 3.1 角色创建模块

**功能**：

- ✅ 角色基本信息编辑
- ✅ 角色卡字段编辑（personality, scenario, first_message 等）
- ✅ 图片上传（头像、背景图）
- ✅ 语音选择
- ✅ 预览功能（实时预览角色对话效果）
- ✅ 保存草稿

**API 设计**：

```python
# 创建角色（草稿）
POST /api/v1/ops/agents/drafts
{
    "name": "角色名称",
    "personality": "性格特点",
    "scenario": "背景设定",
    ...
}

# 更新草稿
PUT /api/v1/ops/agents/drafts/{draft_id}

# 提交审核
POST /api/v1/ops/agents/drafts/{draft_id}/submit
```

##### 3.2 审核工作流模块

**功能**：

- ✅ 待审核角色列表
- ✅ 角色详情查看
- ✅ 审核操作（通过/拒绝）
- ✅ 审核意见填写
- ✅ 审核历史记录
- ✅ 批量审核

**审核流程**：

1. 产品经理创建角色并提交审核
2. 运营人员接收审核任务
3. 查看角色详情和预览
4. 填写审核意见
5. 批准或拒绝
6. 如果批准，进入发布流程
7. 如果拒绝，返回给创建者修改

**API 设计**：

```python
# 获取待审核角色列表
GET /api/v1/ops/agents/pending

# 获取审核任务详情
GET /api/v1/ops/agents/{agent_id}/review

# 提交审核结果
POST /api/v1/ops/agents/{agent_id}/review
{
    "action": "approve" | "reject",
    "comment": "审核意见",
    "reviewer_id": "审核人员ID"
}
```

##### 3.3 发布管理模块

**功能**：

- ✅ 已审核通过角色列表
- ✅ 发布计划（定时发布）
- ✅ 发布历史
- ✅ 版本管理
- ✅ 回滚功能

**发布流程**：

1. 审核通过的角色进入发布队列
2. 产品经理选择发布时间
3. 系统自动在指定时间发布
4. 发布后角色状态变为 `LIVE`
5. 角色出现在用户推荐列表中

**API 设计**：

```python
# 获取可发布角色列表
GET /api/v1/ops/agents/approved

# 创建发布计划
POST /api/v1/ops/agents/{agent_id}/publish
{
    "scheduled_at": "2024-01-01T00:00:00Z",  # 可选，立即发布则省略
    "version": "1.0"
}

# 取消发布
POST /api/v1/ops/agents/{agent_id}/unpublish

# 获取发布历史
GET /api/v1/ops/agents/{agent_id}/publish-history
```

##### 3.4 数据分析模块

**功能**：

- ✅ 角色使用统计
- ✅ 用户互动数据
- ✅ 角色热度排名
- ✅ 发布效果分析

**数据源**：

- **BigQuery**：历史数据分析、报表生成
- **Read Replica**：实时数据查询

### 4. 数据库设计增强

#### 4.1 新增表结构

```sql
-- 审核记录表
CREATE TABLE agent_reviews (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    reviewer_id UUID REFERENCES users(id),
    status VARCHAR(20),  -- APPROVED, REJECTED
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 发布记录表
CREATE TABLE agent_publish_history (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    version VARCHAR(20),
    published_by UUID REFERENCES users(id),
    published_at TIMESTAMP,
    unpublished_at TIMESTAMP,
    status VARCHAR(20)  -- PUBLISHED, UNPUBLISHED
);

-- 角色草稿表（可选，用于保存未提交的草稿）
CREATE TABLE agent_drafts (
    id UUID PRIMARY KEY,
    agent_data JSONB,
    creator_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

#### 4.2 扩展 Agent 模型

```python
# 在 Agent 模型中新增字段
class Agent(Base):
    # ... 现有字段 ...
    
    # 审核相关
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)
    
    # 发布相关
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String, ForeignKey("users.id"), nullable=True)
    scheduled_publish_at = Column(DateTime(timezone=True), nullable=True)
    
    # 版本管理
    version = Column(String, default="1.0")
    parent_version_id = Column(String, nullable=True)  # 父版本ID，用于版本追踪
```

### 5. 权限与安全

#### 5.1 角色权限

**产品经理（Product Manager）**：

- ✅ 创建角色
- ✅ 编辑自己的角色
- ✅ 提交审核
- ✅ 查看自己的角色数据

**运营人员（Operations）**：

- ✅ 审核角色
- ✅ 发布角色
- ✅ 查看所有角色数据
- ✅ 数据分析

**管理员（Admin）**：

- ✅ 所有权限
- ✅ 用户管理
- ✅ 系统配置

#### 5.2 认证与授权

- **独立认证系统**：运营平台使用独立的 JWT 认证
- **角色基础访问控制（RBAC）**：基于用户角色控制访问
- **API 密钥管理**：为运营平台生成专用 API 密钥
- **审计日志**：记录所有关键操作

### 6. 实施计划

#### 阶段 1：基础架构（2-3 周）

- [ ] 完善 `eval_app/` 独立部署
- [ ] 配置数据库分离（BigQuery + Read Replica）
- [ ] 建立独立的认证系统
- [ ] 迁移现有功能到独立平台

#### 阶段 2：角色管理（3-4 周）

- [ ] 实现角色创建模块
- [ ] 实现草稿保存功能
- [ ] 实现角色预览功能
- [ ] 完善角色编辑界面

#### 阶段 3：审核工作流（2-3 周）

- [ ] 实现审核状态管理
- [ ] 实现审核界面
- [ ] 实现审核历史记录
- [ ] 实现通知系统（审核结果通知）

#### 阶段 4：发布管理（2-3 周）

- [ ] 实现发布流程
- [ ] 实现定时发布
- [ ] 实现版本管理
- [ ] 实现发布历史

#### 阶段 5：数据分析（2-3 周）

- [ ] 集成 BigQuery 查询
- [ ] 实现数据分析仪表板
- [ ] 实现报表生成
- [ ] 实现数据导出

### 7. 技术栈

**后端**：

- FastAPI（Python）
- SQLAlchemy（ORM）
- Alembic（数据库迁移）
- Google Cloud BigQuery Client
- PostgreSQL（通过 Read Replica）

**前端**：

- React + TypeScript
- Vite（构建工具）
- React Query（数据获取）
- Ant Design / Material-UI（UI 组件库）

**基础设施**：

- Google Cloud Platform
- Cloud SQL（PostgreSQL）
- BigQuery（数据分析）
- Cloud Storage（文件存储）

### 8. 参考文档

- [运营平台数据库分离方案](./OPS_PLATFORM_DB.md)
- [角色运营文档](./CHAR_OPS.md)
- [IntyEval README](../eval_app/README.md)
- [Evaluation README](../evaluation/README.md)

---

*CREATED_BY_AGENT*

