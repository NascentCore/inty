# 运营平台功能特性依赖分析

*CREATED_BY_AGENT*

## 概述

本文档基于 `evaluation/` 目录下的代码分析，明确运营平台当前依赖的所有功能特性。

## 核心功能模块

### 1. 智能体（AI 角色）管理

**页面**：`pages/AgentManagePage.tsx`

**核心功能**：

- ✅ **创建智能体**
  - 基本信息：名称、性别、简介、开场白
  - 角色卡字段：personality（性格）、scenario（背景设定）、first_message、message_example
  - 图片管理：头像上传与裁剪、背景图上传与裁剪、背景动图生成
  - 语音选择：从可用音色列表中选择
  - LLM 配置：自定义模型配置（model, temperature, max_tokens 等）
  - 元数据：评分、备注信息

- ✅ **编辑智能体**
  - 更新所有字段
  - 图片替换
  - 配置修改

- ✅ **删除智能体**
  - 软删除支持

- ✅ **查看智能体详情**
  - 完整信息展示
  - JSON 格式查看

- ✅ **搜索与筛选**
  - 按名称搜索
  - 按可见性筛选（PUBLIC/PRIVATE）
  - 按性别筛选
  - 按标签筛选
  - 按背景动图状态筛选

- ✅ **分页显示**

**依赖的 API**：

```typescript
// 基础 CRUD
GET    /api/v1/ai/agents/me          // 获取我的智能体列表
GET    /api/v1/ai/agents/{agent_id}  // 获取智能体详情
POST   /api/v1/ai/agents              // 创建智能体
PUT    /api/v1/ai/agents/{agent_id}   // 更新智能体
DELETE /api/v1/ai/agents/{agent_id}  // 删除智能体

// 推荐和搜索
GET    /api/v1/ai/agents/recommend   // 获取推荐智能体
GET    /api/v1/ai/agents/search      // 搜索智能体

// 图片上传
POST   /api/v1/images                 // 上传头像（支持裁剪）
POST   /api/v1/evaluation/agents/{agent_id}/upload-cropped-background  // 上传裁剪后的背景图

// 背景动图生成
POST   /api/v1/ai/agents/{agent_id}/generate-background-animated  // 生成背景动图
GET    /api/v1/evaluation/agents/{agent_id}/check-background-aspect-ratio  // 检查背景图宽高比

// Prompt 管理
GET    /api/v1/ai/agents/prompts/available  // 获取可用 prompt 列表

// 模型列表
GET    /api/v1/ai/agents/models/openrouter  // 获取 OpenRouter 模型列表
```

**依赖的数据模型**：

- `Agent`：智能体基础信息
- `AgentCreateRequest`：创建请求
- `AgentUpdateRequest`：更新请求
- `AgentMetaData`：元数据（评分、备注）
- `LLMConfig`：LLM 配置
- `AvatarCropData`：头像裁剪数据

### 2. 智能体评测系统

**页面**：`pages/EvaluationPage.tsx`、`pages/EvaluationHistoryPage.tsx`

**核心功能**：

- ✅ **创建评测会话**
  - 选择多个智能体
  - 配置测试问题（支持文件上传）
  - 选择评分模型
  - 设置评分标准
  - 配置并行限制和超时

- ✅ **启动评测**
  - 实时监控评测进度
  - WebSocket 连接获取实时更新

- ✅ **查看评测结果**
  - 每个智能体对每个问题的回答
  - 评分和反馈
  - 详细统计信息

- ✅ **评测历史**
  - 查看历史评测会话
  - 对比多个会话结果
  - 导出评测结果（JSON/CSV/XLSX）

- ✅ **评测模板管理**
  - 创建、编辑、删除模板
  - 模板复用

**依赖的 API**：

```typescript
// 评测会话
POST   /api/v1/evaluation/sessions                    // 创建评测会话
GET    /api/v1/evaluation/sessions                    // 获取评测会话列表
GET    /api/v1/evaluation/sessions/{session_id}       // 获取评测会话详情
POST   /api/v1/evaluation/sessions/{session_id}/start // 启动评测
POST   /api/v1/evaluation/sessions/{session_id}/cancel // 取消评测
GET    /api/v1/evaluation/sessions/{session_id}/results // 获取评测结果
DELETE /api/v1/evaluation/sessions/{session_id}       // 删除评测会话
POST   /api/v1/evaluation/sessions/batch              // 批量创建评测会话
POST   /api/v1/evaluation/sessions/compare            // 对比评测会话

// WebSocket 监控
WS     /api/v1/evaluation/sessions/{session_id}/monitor // 实时监控评测进度

// 评测模板
GET    /api/v1/evaluation/templates                   // 获取模板列表
POST   /api/v1/evaluation/templates                   // 创建模板
GET    /api/v1/evaluation/templates/{template_id}     // 获取模板详情
PUT    /api/v1/evaluation/templates/{template_id}     // 更新模板
DELETE /api/v1/evaluation/templates/{template_id}    // 删除模板

// 问题管理
POST   /api/v1/evaluation/questions/parse             // 解析问题文件
POST   /api/v1/evaluation/questions/validate         // 验证问题列表

// 评分模型
GET    /api/v1/evaluation/models                      // 获取可用评分模型
POST   /api/v1/evaluation/scoring-criteria/validate   // 验证评分标准

// 统计和导出
GET    /api/v1/evaluation/stats                       // 获取统计信息
POST   /api/v1/evaluation/results/export             // 导出评测结果
```

**依赖的数据模型**：

- `EvaluationSession`：评测会话
- `EvaluationConfig`：评测配置
- `EvaluationResult`：评测结果
- `EvaluationTemplate`：评测模板
- `ScoringModel`：评分模型
- `EvaluationStats`：统计信息

### 3. 单角色聊天

**页面**：`pages/ChatPage.tsx`

**核心功能**：

- ✅ **聊天会话管理**
  - 创建新会话
  - 查看会话列表
  - 删除会话

- ✅ **消息发送与接收**
  - 文本消息
  - 图片消息
  - 流式响应支持

- ✅ **消息管理**
  - 查看消息历史（分页）
  - 清除消息
  - 消息投票（like/dislike）

- ✅ **图片生成**
  - 基于消息生成图片
  - 查看生成的图片

- ✅ **语音功能**
  - 生成消息语音
  - 语音播放

- ✅ **聊天设置**
  - Premium 模式切换
  - 语言设置
  - 语音开关
  - 风格提示词

**依赖的 API**：

```typescript
// 聊天会话
GET    /api/v1/chats/                                 // 获取聊天列表
POST   /api/v1/chats/                                 // 创建聊天会话
DELETE /api/v1/chats/{chat_id}                        // 删除聊天会话

// 消息
POST   /api/v1/chat/completions/{agent_id}           // 发送消息（OpenAI 兼容 API）
GET    /api/v1/chats/agents/{agent_id}/detail         // 获取聊天详情和消息历史
GET    /api/v1/chats/agents/{agent_id}/messages       // 获取轻量级消息列表
POST   /api/v1/chats/messages/vote                    // 更新消息投票
POST   /api/v1/chats/agents/{agent_id}/clear-messages // 清除消息

// 图片生成
POST   /api/v1/chat/images/{agent_id}                  // 生成聊天图片

// 语音
POST   /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice // 生成消息语音

// 设置
PUT    /api/v1/chats/agents/{agent_id}/settings       // 更新聊天设置

// 调试
GET    /api/v1/chats/agents/{agent_id}/debug-messages // 获取调试消息
```

### 4. 语音通话

**页面**：`pages/VoiceChatPage.tsx`

**核心功能**：

- ✅ **实时语音对话**
  - WebSocket 连接
  - 音频流传输
  - 双向语音通信

**依赖的 API**：

```typescript
// WebSocket 连接（推测）
WS     /api/v1/voice-chat/{agent_id}  // 语音通话 WebSocket 连接
```

### 5. Live2D 情绪聊天

**页面**：`pages/Live2DEmotionChatDemo.tsx`

**核心功能**：

- ✅ **基于 Gemini 情绪标签的背景切换**
  - 实时情绪检测
  - 动态背景切换

### 6. 角色主题专区管理

**页面**：`pages/CharacterThemeManagePage.tsx`

**核心功能**：

- ✅ **专区管理**
  - 创建、编辑、删除专区
  - 设置专区可见性（PRIMARY/SECONDARY/HIDDEN）

- ✅ **角色管理**
  - 添加角色到专区
  - 从专区移除角色
  - 调整角色顺序

**依赖的 API**：

```typescript
GET    /api/v1/character-themes/                      // 获取专区列表
GET    /api/v1/character-themes/{theme_id}            // 获取专区详情
POST   /api/v1/character-themes/                      // 创建专区
PUT    /api/v1/character-themes/{theme_id}            // 更新专区
DELETE /api/v1/character-themes/{theme_id}            // 删除专区
POST   /api/v1/character-themes/{theme_id}/agents     // 添加角色到专区
DELETE /api/v1/character-themes/{theme_id}/agents/{agent_id} // 从专区移除角色
PUT    /api/v1/character-themes/{theme_id}/agents/reorder // 调整角色顺序
```

### 7. 用户数据分析

**页面**：`pages/UserAnalyticsPage.tsx`、`pages/UserDailyMessagesPage.tsx`

**核心功能**：

- ✅ **用户注册统计**
  - 每日新用户统计（按认证类型）
  - 日期范围筛选

- ✅ **用户活跃度分析**
  - 用户聊天活动数据
  - 对话轮数分布
  - 用户轮数分布

- ✅ **热门角色排行**
  - 按用户数、对话轮数、平均轮数等排序
  - 会话留存率统计

- ✅ **用户限制分析**
  - 达到聊天限制的用户统计

- ✅ **角色数据分析**
  - 每个角色的使用统计
  - 会话留存率

- ✅ **用户会话详情**
  - 查看用户的所有会话
  - 查看会话的详细消息

- ✅ **LLM 延迟统计**
  - 按小时统计平均延迟

- ✅ **用户每日消息统计**
  - 按用户查询每日消息和会话数
  - 查看用户当日统计
  - 查看用户会话列表
  - 查看会话消息历史

**依赖的 API**：

```typescript
GET    /api/v1/evaluation/user-analytics/stats                    // 获取统计数据
GET    /api/v1/evaluation/user-analytics/new-users               // 获取新用户统计
GET    /api/v1/evaluation/user-analytics/user-activity           // 获取用户活动数据
GET    /api/v1/evaluation/user-analytics/conversation-rounds      // 获取对话轮数分布
GET    /api/v1/evaluation/user-analytics/user-rounds-distribution // 获取用户轮数分布
GET    /api/v1/evaluation/user-analytics/popular-agents           // 获取热门角色排行
GET    /api/v1/evaluation/user-analytics/users-hitting-limit      // 获取达到限制的用户
GET    /api/v1/evaluation/user-analytics/agent-analytics          // 获取角色数据分析
GET    /api/v1/evaluation/user-analytics/user-sessions-detail     // 获取用户会话详情
GET    /api/v1/evaluation/user-analytics/conversations-detail      // 获取对话详情
GET    /api/v1/evaluation/user-analytics/user-daily-messages       // 获取用户每日消息
GET    /api/v1/evaluation/user-analytics/user-today-stats         // 获取用户当日统计
GET    /api/v1/evaluation/user-analytics/user-sessions            // 获取用户会话列表
GET    /api/v1/evaluation/user-analytics/session-messages         // 获取会话消息历史
GET    /api/v1/evaluation/user-analytics/llm-latency              // 获取 LLM 延迟统计
```

### 8. 生成图片管理

**页面**：`pages/GeneratedImagesPage.tsx`

**核心功能**：

- ✅ **查看生成图片**
  - 按角色查看所有生成的图片
  - 查看图片元数据（生成提示词、尺寸、创建时间等）

- ✅ **图片统计**
  - 各角色的图片数量统计

**依赖的 API**：

```typescript
GET    /api/v1/evaluation/agents/{agent_id}/generated-images      // 获取角色生成图片列表
GET    /api/v1/evaluation/agents/generated-images/counts         // 获取图片数量统计
```

### 9. 举报与反馈管理

**页面**：`pages/ReportFeedbackPage.tsx`

**核心功能**：

- ✅ **查看举报/反馈列表**
  - 按类型筛选（USER/AGENT）
  - 按状态筛选（PENDING/PROCESSING/RESOLVED/REJECTED）
  - 按报告类型筛选（REPORT/FEEDBACK）

- ✅ **删除举报/反馈记录**

**依赖的 API**：

```typescript
GET    /api/v1/report/                              // 获取举报/反馈列表
DELETE /api/v1/report/{report_id}                   // 删除举报/反馈记录
```

### 10. 系统设置

**页面**：`pages/SettingsPage.tsx`

**核心功能**：

- ✅ **图片生成配置**
  - 提示词模板设置
  - 默认历史消息数量设置

**依赖的 API**：

```typescript
GET    /api/v1/ai/agents/image-generation/config     // 获取图片生成配置
PUT    /api/v1/ai/agents/image-generation/config     // 更新图片生成配置
```

### 11. 音色管理

**功能**：在智能体创建/编辑时使用

**核心功能**：

- ✅ **获取音色列表**
  - 搜索音色
  - 按类型、分类、提供商筛选

**依赖的 API**：

```typescript
GET    /api/v1/text-to-speech/list-voices            // 获取音色列表
```

### 12. 用户管理

**功能**：用于提示词查询等功能

**核心功能**：

- ✅ **搜索用户**
  - 按关键词搜索
  - 分页显示

**依赖的 API**：

```typescript
GET    /api/v1/users                                  // 搜索用户列表
```

### 13. 图片生成（文本生成图片）

**功能**：独立的文本生成图片功能

**依赖的 API**：

```typescript
POST   /api/v1/ai/agents/text-to-image               // 文本生成图片
```

## 认证与授权

### API Key 管理

**实现**：`hooks/useApiKey.tsx`、`components/ApiKeyModal.tsx`

**功能**：

- ✅ API Key 输入和验证
- ✅ 本地存储 API Key
- ✅ 全局 API Key 管理

**依赖**：

- 所有 API 请求都需要 Bearer Token 认证
- API Key 通过 `Authorization: Bearer {api_key}` 传递

## 数据依赖总结

### 数据库表依赖

根据 API 调用和类型定义，运营平台依赖以下数据库表：

1. **agents** - 智能体表
2. **users** - 用户表
3. **chats** - 聊天会话表
4. **chat_messages** - 聊天消息表
5. **evaluation_sessions** - 评测会话表
6. **evaluation_results** - 评测结果表
7. **evaluation_templates** - 评测模板表
8. **character_themes** - 角色主题表
9. **character_theme_agents** - 角色主题关联表
10. **reports** - 举报/反馈表
11. **chat_settings** - 聊天设置表
12. **generated_images** - 生成图片表（推测）

### 外部服务依赖

1. **Google Cloud Storage (GCS)**
   - 图片存储（头像、背景图、生成图片）
   - 音频文件存储

2. **OpenRouter API**
   - 模型列表获取
   - LLM 调用（通过后端）

3. **Gemini API**
   - 情绪检测（Live2D 功能）
   - LLM 调用（通过后端）

4. **ElevenLabs / Google TTS**
   - 语音生成（通过后端）

5. **图片生成服务**
   - 文本生成图片（通过后端）

## 前端技术栈

- **React 18+**
- **TypeScript**
- **Vite**（构建工具）
- **Ant Design**（UI 组件库）
- **React Plotly.js**（图表库）
- **WebSocket**（实时通信）

## 后端 API 依赖

### API 响应格式

所有 API 遵循统一响应格式：

```typescript
interface ApiResponse<T> {
  code: number;      // 200 表示成功
  message: string;   // 消息
  data: T;           // 数据
}
```

### 分页格式

```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}
```

## 关键功能缺失分析

### 当前缺失的功能

1. **角色审核工作流**
   - ❌ 没有审核界面
   - ❌ 没有审核状态管理
   - ❌ 状态字段存在但无法在界面操作

2. **角色发布管理**
   - ❌ 没有发布流程
   - ❌ 没有版本管理
   - ❌ 没有发布历史

3. **权限管理**
   - ❌ 所有功能对所有用户开放
   - ❌ 没有角色权限区分

4. **数据分离**
   - ⚠️ 直接访问生产数据库
   - ⚠️ 可能影响生产性能

## 建议的改进方向

1. **添加审核工作流**
   - 实现审核界面
   - 添加审核状态管理
   - 实现审核历史记录

2. **添加发布管理**
   - 实现发布流程
   - 添加版本管理
   - 实现发布历史

3. **数据分离**
   - 使用 BigQuery 进行数据分析查询
   - 使用 Read Replica 进行实时查询
   - 减少对生产数据库的压力

4. **权限系统**
   - 实现基于角色的访问控制（RBAC）
   - 区分产品经理、运营人员、管理员权限

---

*CREATED_BY_AGENT*

