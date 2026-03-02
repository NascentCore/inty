# 性能监控页面功能实施文档

CREATED_BY_AGENT

## 概述

创建了一个独立的"性能监控"页面，将 LLM 调用延迟、生图延迟从用户数据分析页面中分离出来，并新增 Live Chat 相关的统计和延迟趋势数据。

## 实施内容

### 1. 后端开发

#### 1.1 新增 Schema 定义

**文件**: `app/schemas/user_analytics.py`

新增以下数据模型：

- `LiveChatLatencyItem`: Live Chat 延迟统计项
  - `hour`: 小时时间戳
  - `avg_connect_latency`: 平均连接延迟（毫秒）
  - `avg_first_response_after_silence`: 平均静默后首响应延迟（毫秒）
  - `avg_turn_latency`: 平均轮次延迟（毫秒）
  - `count`: 会话数量
- `LiveChatLatencyResponse`: Live Chat 延迟趋势响应
- `LiveChatBasicStatsResponse`: Live Chat 基础统计响应
  - `total_users`: 发起语音通话人数
  - `total_sessions`: 总会话数
  - `total_duration`: 总通话时长（秒）
  - `avg_sessions_per_user`: 人均语音通话次数
  - `avg_duration_per_user`: 人均通话时长（秒）
  - `avg_duration_per_session`: 每 session 平均时长（秒）

#### 1.2 新增 Service 方法

**文件**: `app/services/user_analytics_service.py`

新增以下方法：

- `get_live_chat_latency_trend(activity_start_date, activity_end_date)`: 按小时聚合 Live Chat 延迟数据
  - 从 `subscription_usage` 表中查询
  - 从 `extra_data->'latency_metrics'` JSON 字段提取延迟数据
  - 按小时分组聚合
- `get_live_chat_basic_stats(activity_start_date, activity_end_date)`: 获取 Live Chat 基础统计
  - 统计用户数、会话数、总时长
  - 计算平均值

#### 1.3 新增 API 端点

**文件**: `backend/ops/api/v1/evaluation.py`

新增以下端点：

- `GET /evaluation/user-analytics/live-chat-latency`
  - 参数：`activity_start_date`, `activity_end_date`, `activity_last_days`
  - 返回：Live Chat 延迟趋势数据
  - 默认查询最近 7 天
- `GET /evaluation/user-analytics/live-chat-stats`
  - 参数：`activity_start_date`, `activity_end_date`, `activity_last_days`
  - 返回：Live Chat 基础统计数据
  - 默认查询最近 7 天

### 2. 前端开发

#### 2.1 新增类型定义

**文件**: `evaluation/types.ts`

新增以下类型：

- `LiveChatLatencyItem`
- `LiveChatLatencyResponse`
- `LiveChatBasicStatsResponse`

#### 2.2 更新 API 服务层

**文件**: `evaluation/services/api.ts`

在 `userAnalyticsApi` 对象中新增：

- `getLiveChatLatency(params)`: 获取 Live Chat 延迟趋势
- `getLiveChatStats(params)`: 获取 Live Chat 基础统计

#### 2.3 创建性能监控页面

**文件**: `evaluation/pages/PerformanceAnalyticsPage.tsx`

新建页面组件，包含：

- **日期筛选器**：最近 7 天、最近 30 天、最近 90 天、全部
- **统计卡片区**：展示 Live Chat 基础统计（4 个卡片）
  - 语音通话用户数
  - 总会话数
  - 总通话时长
  - 平均会话时长
- **LLM 延迟趋势图表**：折线图
- **生图延迟趋势图表**：按模型分组的折线图
- **Live Chat 延迟趋势图表**：三条折线
  - 连接延迟
  - 首字节延迟
  - 平均轮次延迟

#### 2.4 修改用户数据分析页面

**文件**: `evaluation/pages/UserAnalyticsPage.tsx`

移除以下内容：

- LLM 延迟趋势图表
- 生图延迟趋势图表
- 相关状态变量和 API 调用

#### 2.5 更新路由和导航

**文件**: `evaluation/App.tsx`

- 导入 `PerformanceAnalyticsPage` 组件
- 导入 `DashboardOutlined` 图标
- 在 `PageKey` 类型中添加 `"performance-analytics"`
- 在 `navigationItems` 数组中添加新导航项
- 在 `getPageTitle()` 中添加标题映射
- 在 `renderPageContent()` 中添加路由处理

## 数据存储说明

Live Chat 的延迟数据存储在 `subscription_usage` 表的 `extra_data` JSON 字段中：

```json
{
  "latency_metrics": {
    "connect_latency_ms": 123,
    "first_response_after_silence_ms": 456,
    "avg_turn_latency_ms": 789
  }
}
```

这些数据在 Live Chat 会话结束时由 `app/api/v1/endpoints/live_chat.py` 自动记录。

## 测试步骤

### 后端测试

1. 启动后端服务
2. 使用 API 测试工具（如 Postman）测试新端点：
   ```
   GET /api/v1/evaluation/user-analytics/live-chat-latency?activity_last_days=7
   GET /api/v1/evaluation/user-analytics/live-chat-stats?activity_last_days=7
   ```
3. 验证返回数据格式是否正确

### 前端测试

1. 启动前端开发服务器
2. 登录评测系统
3. 在导航菜单中找到"性能监控"菜单项
4. 点击进入性能监控页面
5. 测试以下功能：
   - 页面是否正常加载
   - 统计卡片是否显示正确数据
   - 三个图表是否正常渲染
   - 时间范围筛选器是否工作正常
   - 刷新按钮是否正常工作
6. 切换到"用户数据分析"页面，验证：
   - LLM 延迟趋势图表已被移除
   - 生图延迟趋势图表已被移除
   - 其他图表和功能正常

## 潜在问题和注意事项

1. **数据可用性**：Live Chat 延迟数据只在用户进行语音通话后才会产生。如果没有用户使用过 Live Chat 功能，延迟图表将显示"暂无数据"。

2. **性能考虑**：如果 `subscription_usage` 表数据量很大，查询可能较慢。建议在 `created_at` 和 `usage_type` 字段上添加索引。

3. **时区处理**：所有时间聚合使用 UTC 时区，确保时间一致性。

4. **空值处理**：某些 Live Chat 会话可能没有完整的延迟数据（例如连接失败的会话），这些会话在图表中显示为 null 值，折线图会自动跳过这些点。

## 相关文件清单

### 后端文件

- `app/schemas/user_analytics.py`
- `app/services/user_analytics_service.py`
- `backend/ops/api/v1/evaluation.py`

### 前端文件

- `evaluation/types.ts`
- `evaluation/services/api.ts`
- `evaluation/pages/PerformanceAnalyticsPage.tsx` (新建)
- `evaluation/pages/UserAnalyticsPage.tsx` (修改)
- `evaluation/App.tsx`

## 完成日期

2026-01-14
