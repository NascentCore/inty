# Firebase 参数类型指南：自定义维度、自定义指标、计算指标

## 概述

本文档详细解释 Firebase Analytics 中的三种参数类型：**自定义维度**、**自定义指标**和**计算指标**，并列出本项目中所有参数的分类。

## 一、三种参数类型的区别

### 1.1 自定义维度（Custom Dimensions）

**定义**：用于对事件进行**分组和筛选**的字符串类型参数。

**特点**：
- **数据类型**：字符串（String）
- **用途**：用于分类、分组、筛选数据
- **限制**：每个项目最多 **50 个自定义维度**（40 个文本维度 + 10 个数值维度）
- **示例**：`agent_id`、`user_type`、`page_name`

**使用场景**：
- 按 Agent 分组统计消息发送量
- 按用户类型（vip/free）筛选数据
- 按页面名称分析用户行为

**在代码中的实现**：
```kotlin
// String 类型 → 自定义维度
bundle.putString("agent_id", agentId)
bundle.putString("user_type", "vip")
```

### 1.2 自定义指标（Custom Metrics）

**定义**：用于**量化测量**的数值类型参数。

**特点**：
- **数据类型**：数值（Long、Int、Double、Float）
- **用途**：用于计算平均值、总和、最大值等统计指标
- **限制**：每个项目最多 **50 个自定义指标**（40 个数值指标 + 10 个文本指标）
- **示例**：`ai_response_time`、`message_length`、`timestamp`

**使用场景**：
- 计算平均响应时间
- 统计消息总长度
- 分析页面停留时长

**在代码中的实现**：
```kotlin
// Long/Int 类型 → 自定义指标
bundle.putLong("ai_response_time", responseTime)
bundle.putInt("message_length", messageLength)
bundle.putDouble("discount_rate", discountRate)
```

### 1.3 计算指标（Calculated Metrics）

**定义**：基于现有指标**自动计算**的派生指标，**不占用自定义指标配额**。

**特点**：
- **数据类型**：由现有指标计算得出
- **用途**：创建复合指标，如转化率、平均值等
- **限制**：**不占用**自定义指标配额（50 个限制）
- **示例**：`avg_response_time`（基于 `ai_response_time` 计算）、`conversion_rate`（基于事件计数计算）

**使用场景**：
- 计算平均响应时间（总和 / 计数）
- 计算转化率（成功事件数 / 总事件数）
- 计算错误率（错误事件数 / 总事件数）

**创建方式**：
- 在 Firebase 控制台的 **Analytics（分析）** > **计算指标** 中创建
- 基于现有事件和指标进行数学运算

## 二、参数类型判断规则

### 2.1 根据代码中的数据类型判断

| 代码中的类型 | Bundle 中的方法 | Firebase 后台类型 | 说明 |
|------------|---------------|-----------------|------|
| `String` | `putString()` | **自定义维度** | 字符串类型，用于分组和筛选 |
| `Boolean` | `putString()` (转换为 "true"/"false") | **自定义维度** | 布尔值转换为字符串，用于分组和筛选 |
| `Long` | `putLong()` | **自定义指标** | 长整型数值，用于量化测量 |
| `Int` | `putLong()` (转换为 Long) | **自定义指标** | 整型数值，用于量化测量 |
| `Double` | `putDouble()` | **自定义指标** | 双精度浮点数，用于量化测量 |
| `Float` | `putDouble()` (转换为 Double) | **自定义指标** | 单精度浮点数，用于量化测量 |

### 2.2 判断原则

1. **字符串类型** → **自定义维度**
   - 用于分类、分组、筛选
   - 如：`agent_id`、`user_type`、`page_name`

2. **数值类型** → **自定义指标**
   - 用于量化测量、统计分析
   - 如：`ai_response_time`、`message_length`、`timestamp`

3. **布尔值** → **自定义维度**（转换为字符串）
   - 在代码中转换为 "true"/"false" 字符串
   - 如：`is_auto_play`、`success`

## 三、本项目参数分类清单

### 3.1 自定义维度（字符串类型参数）

#### 核心业务维度（高优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `agent_id` | 事件 | Agent ID | 几乎所有业务事件 |
| `agent_name` | 事件 | Agent 名称 | 几乎所有业务事件 |
| `user_type` | 事件 | 用户类型（vip/free） | 几乎所有业务事件 |
| `message_id` | 事件 | 消息 ID | 消息相关事件 |
| `error_message` | 事件 | 错误消息（包含错误类型和异常类型信息，格式：`failure: ...` 或 `exception: ClassName, ...`） | 失败和错误事件 |
| `message_type` | 事件 | 消息类型（normal/keep_talking） | message_send_* 事件 |

#### 订阅相关维度（高优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `product_id` | 事件 | 订阅商品 ID | subscription_success, subscription_failure, subscription_price_* |
| `product_name` | 事件 | 订阅商品名称 | subscription_price_* |
| `plan_type` | 事件 | 订阅计划类型 | subscription_price_* |
| `order_id` | 事件 | 订单 ID | subscription_success, subscription_failure |
| `purchase_token` | 事件 | 购买令牌 | subscription_success, subscription_failure |
| `currency_code` | 事件 | 货币代码 | subscription_price_displayed |
| `google_play_currency_code` | 事件 | Google Play 货币代码 | subscription_price_fetched |
| `displayed_price` | 事件 | 显示的价格 | subscription_price_displayed |
| `original_price` | 事件 | 原始价格 | subscription_price_displayed |
| `google_play_price` | 事件 | Google Play 价格 | subscription_price_fetched |
| `corrected_price` | 事件 | 修正后的价格 | subscription_price_fetched |
| `old_price` | 事件 | 旧价格 | subscription_price_fetched |
| `old_currency_code` | 事件 | 旧货币代码 | subscription_price_fetched |

#### 页面追踪维度（中优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `page_name` | 事件 | 页面名称 | 页面追踪事件 |
| `page_class` | 事件 | 页面类名 | 页面追踪事件 |
| `page_source` | 事件 | 页面来源 | SCREEN_VIEW |
| `page_type` | 事件 | 页面类型 | SCREEN_VIEW（explore 页面） |

#### Agent切换维度（中优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `switch_method` | 事件 | 切换方法 | agent_switch |
| `from_agent_id` | 事件 | 来源 Agent ID | agent_switch |
| `from_agent_name` | 事件 | 来源 Agent 名称 | agent_switch |
| `to_agent_id` | 事件 | 目标 Agent ID | agent_switch |
| `to_agent_name` | 事件 | 目标 Agent 名称 | agent_switch |

#### 其他维度（中优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `play_status` | 事件 | 播放状态 | audio_play_end |
| `user_logged_out` | 事件 | 用户是否已登出 | auth_failure |
| `is_initial_load` | 事件 | 是否为初始加载 | SCREEN_VIEW（explore 页面） |
| `success` | 事件 | 操作是否成功 | 网络请求相关事件 |
| `image_url` | 事件 | 图片 URL | image_generation_success |
| `audio_url` | 事件 | 音频 URL | audio_play_end |
| `url` | 事件 | 请求 URL | slow_request, very_slow_request, request_failure |
| `method` | 事件 | HTTP 方法 | slow_request, very_slow_request, request_failure |
| `message_timestamp` | 事件 | 消息时间戳 | message_like, message_dislike |

#### 布尔值维度（作为字符串维度）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `is_auto_play` | 事件 | 是否自动播放 | voice_playback_start, audio_play_end |
| `is_manual_click` | 事件 | 是否手动点击 | voice_playback_start |
| `has_audio_url` | 事件 | 是否有音频 URL | voice_playback_start |
| `has_generated_image` | 事件 | 是否有生成的图片 | message_like, message_dislike |
| `is_opening` | 事件 | 是否为开场消息 | message_like, message_dislike |
| `is_selected` | 事件 | 是否被选中 | subscription_price_displayed |
| `is_subscribed` | 事件 | 是否已订阅 | subscription_price_displayed |
| `price_changed` | 事件 | 价格是否变化 | subscription_price_fetched |
| `currency_changed` | 事件 | 货币是否变化 | subscription_price_fetched |
| `micros_changed` | 事件 | 微单位是否变化 | subscription_price_fetched |

**自定义维度总计**：约 **49 个**（在 50 个限制范围内，使用率98%，剩余1个配额）

### 3.2 自定义指标（数值类型参数）

#### 时间相关指标（高优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `timestamp` | 事件 | 事件时间戳（毫秒） | 几乎所有事件 |
| `ai_response_time` | 事件 | AI响应时间（毫秒） | message_send_success, message_send_error |
| `end_to_end_time` | 事件 | 端到端时间（毫秒） | message_send_* |
| `response_time` | 事件 | 接口响应时间（毫秒） | explore_agents_fetch_* |
| `generation_time_ms` | 事件 | 图片生成耗时（毫秒） | image_generation_* |
| `play_duration` | 事件 | 播放时长（毫秒） | audio_play_end |
| `time_spent` | 事件 | 页面停留时长（毫秒） | page_leave |
| `visible_time_spent` | 事件 | 页面可见时长（毫秒） | page_leave |
| `lifecycle_time_spent` | 事件 | 生命周期时长（毫秒） | page_leave |

#### 数量相关指标（高优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `message_length` | 事件 | 消息长度 | message_sent, message_like, message_dislike |
| `image_width` | 事件 | 图片宽度 | image_generation_success |
| `image_height` | 事件 | 图片高度 | image_generation_success |
| `page` | 事件 | 页码 | explore_agents_fetch_* |
| `page_size` | 事件 | 每页大小 | explore_agents_fetch_* |
| `agents_count` | 事件 | 本次返回的 agents 数量 | explore_agents_fetch_success |
| `current_ui_agents_count` | 事件 | 当前UI中所有已加载的 agents 总数 | explore_agents_fetch_* |
| `sort_seed` | 事件 | 排序种子 | explore_agents_fetch_* |
| `selected_plan_index` | 事件 | 选中的计划索引 | subscription_price_displayed |
| `total_plans_count` | 事件 | 计划总数 | subscription_price_displayed |

#### 价格相关指标（高优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `price_micros` | 事件 | 价格（微单位） | subscription_price_displayed |
| `google_play_price_micros` | 事件 | Google Play 价格（微单位） | subscription_price_fetched |
| `old_price_micros` | 事件 | 旧价格（微单位） | subscription_price_fetched |
| `discount_rate` | 事件 | 折扣率 | subscription_price_displayed |

#### 网络请求相关指标（中优先级）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `duration_ms` | 事件 | 请求持续时间（毫秒） | slow_request, very_slow_request, request_failure |
| `response_code` | 事件 | 响应码 | message_send_success, message_send_error |
| `error_code` | 事件 | 错误代码（HTTP错误时使用，如401） | auth_failure, message_send_error, image_generation_failure, subscription_failure |

#### 性能指标参数（通过 logPerformanceMetric 使用）

| 参数名称 | 事件范围 | 说明 | 使用事件 |
|---------|---------|------|---------|
| `metric_value` | 事件 | 指标值 | AI_RESPONSE_TIME, EXPLORE_RESPONSE_TIME, TTS_GENERATION_TIME, IMAGE_GENERATION_TIME |
| `metric_unit` | 事件 | 指标单位 | AI_RESPONSE_TIME, EXPLORE_RESPONSE_TIME, TTS_GENERATION_TIME, IMAGE_GENERATION_TIME |

**自定义指标总计**：约 **25 个**（在 50 个限制范围内，使用率50%，剩余25个配额）

### 3.3 计算指标（建议创建）

以下计算指标**不占用自定义指标配额**，可以在 Firebase 控制台创建：

#### 性能相关计算指标

| 计算指标名称 | 计算公式 | 说明 |
|------------|---------|------|
| `avg_ai_response_time` | `ai_response_time` 的平均值 | 平均 AI 响应时间 |
| `avg_end_to_end_time` | `end_to_end_time` 的平均值 | 平均端到端时间 |
| `avg_generation_time` | `generation_time_ms` 的平均值 | 平均图片生成时间 |
| `p95_ai_response_time` | `ai_response_time` 的 95 分位数 | 95% 的请求响应时间 |

#### 业务相关计算指标

| 计算指标名称 | 计算公式 | 说明 |
|------------|---------|------|
| `message_send_success_rate` | `message_send_success` 计数 / `message_sent` 计数 | 消息发送成功率 |
| `image_generation_success_rate` | `image_generation_success` 计数 / `image_generation_start` 计数 | 图片生成成功率 |
| `explore_fetch_success_rate` | `explore_agents_fetch_success` 计数 / (`explore_agents_fetch_success` + `explore_agents_fetch_failure`) 计数 | Explore 接口成功率 |
| `avg_message_length` | `message_length` 的平均值 | 平均消息长度 |

#### 转化相关计算指标

| 计算指标名称 | 计算公式 | 说明 |
|------------|---------|------|
| `subscription_conversion_rate` | `subscription_success` 计数 / `subscription_price_displayed` 计数 | 订阅转化率 |
| `free_to_vip_conversion_rate` | `subscription_success` 计数 / `free_limit_reached` 计数 | 免费用户转 VIP 转化率 |

## 四、参数配置建议

### 4.1 优先级配置

#### 第一批（立即配置）- 核心业务参数

**自定义维度（25 个核心参数）**：
- `agent_id`、`agent_name`、`user_type`
- `message_id`、`message_type`
- `error_code`、`error_message`
- `product_id`、`product_name`、`plan_type`
- `page_name`、`page_class`、`page_source`
- `switch_method`、`from_agent_id`、`to_agent_id`
- `play_status`
- `is_auto_play`、`has_generated_image`、`is_opening`
- `success`、`user_logged_out`
- `is_initial_load`、`is_selected`、`is_subscribed`

**自定义指标（15 个核心参数）**：
- `timestamp`、`ai_response_time`、`end_to_end_time`
- `response_time`、`generation_time_ms`、`play_duration`
- `time_spent`、`message_length`
- `image_width`、`image_height`
- `page`、`page_size`、`agents_count`
- `duration_ms`、`response_code`

#### 第二批（后续配置）- 扩展参数

**自定义维度（14 个扩展参数）**：
- `order_id`、`purchase_token`、`currency_code`
- `google_play_currency_code`
- `from_agent_name`、`to_agent_name`
- `page_type`、`image_url`、`audio_url`
- `url`、`method`
- `is_manual_click`、`has_audio_url`
- `price_changed`、`currency_changed`、`micros_changed`

**自定义指标（5 个扩展参数）**：
- `current_ui_agents_count`、`sort_seed`
- `price_micros`、`google_play_price_micros`、`discount_rate`

### 4.2 计算指标配置（不占用配额）

建议在 Firebase 控制台创建以下计算指标：

1. **性能指标**：
   - `avg_ai_response_time`
   - `avg_end_to_end_time`
   - `avg_generation_time`
   - `p95_ai_response_time`

2. **业务指标**：
   - `message_send_success_rate`
   - `image_generation_success_rate`
   - `explore_fetch_success_rate`
   - `avg_message_length`

3. **转化指标**：
   - `subscription_conversion_rate`
   - `free_to_vip_conversion_rate`

## 五、总结

### 5.1 参数类型选择原则

1. **字符串类型** → **自定义维度**
   - 用于分组、筛选、分类
   - 如：ID、名称、类型、状态

2. **数值类型** → **自定义指标**
   - 用于量化测量、统计分析
   - 如：时间、长度、数量、价格

3. **复合指标** → **计算指标**
   - 基于现有指标计算
   - 不占用自定义指标配额
   - 如：平均值、成功率、转化率

### 5.2 配额使用情况

- **自定义维度**：约 49 个（在 50 个限制范围内，使用率98%）✅
- **自定义指标**：约 25 个（在 50 个限制范围内，使用率50%）✅
- **计算指标**：不占用配额，可创建多个 ✅

### 5.3 最佳实践

1. **优先配置核心业务参数**：确保关键数据可分析
2. **使用计算指标**：减少自定义指标配额占用
3. **定期审查参数使用**：移除未使用的参数，释放配额
4. **合理使用维度**：避免创建过多低价值维度

---

*文档更新时间：2025年1月*
*版本：dev_1.3.x*
*基于 Firebase Analytics 官方文档和项目实际代码分析*

