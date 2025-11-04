# IntelliMate Firebase Analytics & Performance 事件文档

## 概述

本文档整理了IntelliMate Android应用中所有实际使用的Firebase Analytics和Performance事件，包含事件名称、参数、使用场景和采样配置。基于实际代码分析，确保信息的准确性和实用性。

## 采样配置说明

- **🔴 业务数据点** - 100%采样，确保关键业务数据完整收集
- **🟡 性能相关事件** - 保持现有采样配置，平衡数据质量和成本
- **⚪ 禁用事件** - 完全禁用低价值事件

## 1. Firebase Analytics 事件

### 1.1 Firebase内置事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `APP_OPEN` | IntelliMateApp.kt | 无 | 应用启动事件 | 🔴 100% |
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | `user_id`, `user_type`, `timestamp` | 用户登录（Firebase内置事件） | 🔴 100% |
| `SIGN_UP` | FirebaseManager.Events | 预留 | 用户注册 | 🔴 100% |
| `SCREEN_VIEW` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp`, `page_source` (可选), 其他自定义参数 | 页面访问（Firebase内置事件，通过 `trackPageView()` 自动记录） | 🔴 100% |
| `SELECT_CONTENT` | FirebaseManager.Events | 预留 | 内容选择 | 🔴 100% |
| `SHARE` | FirebaseManager.Events | 预留 | 分享功能 | 🔴 100% |
| `SEARCH` | FirebaseManager.Events | 预留 | 搜索功能 | 🔴 100% |
| `PURCHASE` | FirebaseManager.Events | 预留 | 购买事件 | 🔴 100% |

### 1.2 应用生命周期事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `APP_OPEN` | IntelliMateApp.kt | 无 | 应用启动（Firebase内置事件） | 🔴 100% |
| `BILLING_RELEASE` | IntelliMateApp.kt | 无 | 计费系统释放 | 🔴 100% |

### 1.3 用户认证事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `auth_failure` | UnifiedOkHttpClient.kt | `http_code`, `url`, `user_logged_out` | HTTP 401认证失败 | 🔴 100% |
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | `user_id`, `user_type`, `timestamp` | 用户登录（Firebase内置事件） | 🔴 100% |
| `user_logout` | MainViewModel.kt | `user_id`, `user_type`, `timestamp` | 用户登出 | 🔴 100% |

### 1.4 聊天相关事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `chat_started` | ChatViewModel.kt | `agent_id`, `agent_name`, `user_type`, `timestamp` | 聊天会话开始 | 🔴 100% |
| `message_sent` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_length`, `user_type`, `timestamp` | 消息发送 | 🔴 100% |
| `message_send_success` | ChatViewModel.kt | `agent_id`, `agent_name`, `response_code`, `user_type`, `ai_response_time`, `end_to_end_time` | 消息发送成功（包含API响应时间和端到端时间） | 🔴 100% |
| `message_send_failure` | ChatViewModel.kt | `agent_id`, `agent_name`, `error_message`, `user_type`, `ai_response_time`, `end_to_end_time` | 消息发送失败（包含API响应时间和端到端时间） | 🔴 100% |
| `message_send_exception` | ChatViewModel.kt | `agent_id`, `agent_name`, `error_message`, `user_type`, `end_to_end_time` | 消息发送异常（包含端到端时间） | 🔴 100% |
| `free_limit_reached` | ChatViewModel.kt | `agent_id`, `agent_name`, `user_type`, `timestamp` | 达到免费限制 | 🔴 100% |

### 1.5 图片生成事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `image_generation_start` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `user_type`, `timestamp` | 图片生成开始 | 🔴 100% |
| `image_generation_success` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `image_url`, `image_width`, `image_height`, `user_type`, `generation_time_ms`, `timestamp` | 图片生成成功（包含图片信息和生成耗时） | 🔴 100% |
| `image_generation_failure` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `error_code`, `error_message`, `error_type`（异常时）, `user_type`, `generation_time_ms`, `timestamp` | 图片生成失败（包含错误信息和生成耗时） | 🔴 100% |
| `image_generation_limit_reached` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `error_code`, `error_message`, `user_type`, `generation_time_ms`, `timestamp` | 图片生成限制达到（需要订阅） | 🔴 100% |

### 1.6 页面追踪事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `SCREEN_VIEW` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp`, `page_source` (可选), 其他自定义参数 | 页面访问（Firebase内置事件，通过 `trackPageView()` 自动记录） | 🔴 100% |
| `page_leave` | PageTrackingHelper.kt | `page_name`, `page_class`, `time_spent`, `visible_time_spent`, `lifecycle_time_spent`, `timestamp` | 页面离开，记录停留时长 | 🔴 100% |
| `page_visible` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp` | 页面变为可见 | ⚪ 禁用 |
| `page_hidden` | PageTrackingHelper.kt | `page_name`, `page_class`, `visible_time_spent`, `timestamp` | 页面变为不可见 | ⚪ 禁用 |
| `page_lifecycle` | PageTrackingHelper.kt | `page_name`, `page_class`, `lifecycle_event`, `lifecycle_time_spent`, `timestamp` | 页面生命周期事件 | ⚪ 禁用 |
| `explore_page_view` | ExploreViewModel.kt | `page_type` (recommendations), `is_initial_load` (true/false) | 探索页面访问 | 🔴 100% |

**页面来源参数说明：**
- `page_source`：页面来源标识，用于统计用户从哪个入口进入页面
  - **VipCenterActivity**：`home_expired_dialog`（首页过期VIP对话框）、`chat_page`（聊天页面）、`chat_more_panel`（聊天更多面板）、`profile_upgrade`（个人中心升级按钮）、`settings_subscription`（设置页面订阅管理）、`settings_premium_dialog`（设置页面高级模型对话框）
  - **ChatActivity**：`messages_tab`（消息列表Tab）、`explore_tab`（探索Tab）、`profile_tab`（个人中心Tab）
  - **ChatPage**：`chat_activity`（在 ChatActivity 中）、`main_activity_home_tab`（在 MainActivity 的 HorizontalPager 中）

### 1.7 Explore 数据加载事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `explore_agents_fetch_success` | ExploreViewModel.kt | `page`, `page_size`, `response_time`, `agents_count`, `current_ui_agents_count`, `sort_seed`, `user_type`, `timestamp` | Explore接口请求成功（包含本次返回数量和当前UI累计总数） | 🔴 100% |
| `explore_agents_fetch_failure` | ExploreViewModel.kt | `page`, `page_size`, `response_time`, `error_message`, `current_ui_agents_count`, `sort_seed`, `user_type`, `timestamp` | Explore接口请求失败 | 🔴 100% |
| `explore_agents_fetch_exception` | ExploreViewModel.kt | `page`, `page_size`, `response_time`, `exception_type`, `exception_message`, `current_ui_agents_count`, `sort_seed`, `user_type`, `timestamp` | Explore接口请求异常 | 🔴 100% |

### 1.8 用户交互事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `user_interaction` | PageTrackingHelper.kt | `action`, `target`, `current_page`, `timestamp` | 用户交互行为 | 🟡 调试100%，发布100% |
| `agent_switch` | ChatViewModel.kt | `from_agent_id`, `from_agent_name`, `to_agent_id`, `to_agent_name`, `switch_method`, `user_type`, `timestamp` | Agent切换 | 🔴 100% |
| `voice_playback_start` | AudioManager.kt | `message_id`, `agent_id`, `agent_name`, `has_audio_url`, `auto_play`, `is_manual_click`, `timestamp` | 语音播放开始 | 🔴 100% |
| `audio_play_end` | VoicePlayer.kt | `agent_id`, `agent_name`, `message_id`, `is_auto_play`, `play_status`, `play_duration`, `audio_url`, `timestamp` | 语音播放结束（播放完成或暂停时触发） | 🔴 100% |
| `pull_up_input` | ChatInput.kt | `agent_id`, `agent_name`, `timestamp` | 拉起输入框（键盘弹出时触发） | 🔴 100% |
| `image_show_success` | AgentBackground.kt | `agent_id`, `agent_name`, `image_url`, `image_width`, `image_height`, `content_scale`, `timestamp` | 图片显示成功 | 🔴 100% |

### 1.9 订阅与计费事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `subscription_start` | BillingPurchaseManager.kt | `product_id`, `subscription_id`, `purchase_time`, `order_id`, `user_type`, `timestamp` | 订阅开始（订阅验证成功时触发） | 🔴 100% |
| `subscription_price_fetched` | BillingPriceManager.kt | `product_id`, `product_name`, `plan_type`, `google_play_price`, `google_play_currency_code`, `google_play_price_micros`, `corrected_price`, `old_price`, `old_currency_code`, `old_price_micros`, `has_placeholder`, `price_changed`, `currency_changed`, `micros_changed` | 从Google Play获取到的订阅价格详细信息（包含价格变化对比） | 🔴 100% |
| `subscription_price_displayed` | VipCenterContent.kt | `product_id`, `product_name`, `plan_type`, `displayed_price`, `currency_code`, `price_micros`, `discount_rate`, `original_price`, `is_selected`, `selected_plan_index`, `total_plans_count`, `is_subscribed`, `timestamp` | UI上显示的订阅价格详细信息（包含选择状态和订阅状态） | 🔴 100% |

### 1.10 网络请求事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `network_request` | PageTrackingHelper.kt | `url`, `method`, `success`, `response_time`, `current_page` | 网络请求（通用） | 🟡 调试100%，发布20% |
| `network_retry` | UnifiedOkHttpClient.kt | 预留（配置中已定义，但代码中未使用） | 网络请求重试 | 🟡 调试100%，发布50% |
| `slow_request` | UnifiedOkHttpClient.kt | `duration_ms`, `method`, `url`, `successful` | 慢请求（>3秒） | 🟡 调试100%，发布30% |
| `very_slow_request` | UnifiedOkHttpClient.kt | `duration_ms`, `method`, `url`, `successful` | 极慢请求（>10秒） | 🔴 100% |
| `request_failure` | UnifiedOkHttpClient.kt | `duration_ms`, `method`, `url`, `error_type`, `error_message` | 请求失败（网络请求失败时触发） | 🔴 100% |

### 1.11 错误监控事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `app_error` | PageTrackingHelper.kt, UnifiedOkHttpClient.kt | `error`, `error_type`, `current_page`, `page_class`, `timestamp` | 应用错误 | 🔴 100% |

### 1.12 性能指标事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `performance_metric` | FirebaseManager.logPerformanceMetric() | `metric_name`, `metric_value`, `metric_unit`, `timestamp` | 性能指标（通用性能指标记录） | 🔴 100% |

## 2. Firebase Performance 性能监控

### 2.1 性能事件常量

| 事件名称 | 使用位置 | 业务含义 | 采样率 |
|---------|---------|---------|--------|
| `AI_RESPONSE_TIME` | ChatViewModel.kt | AI响应时间（API调用时间） | 🔴 100% |
| `EXPLORE_RESPONSE_TIME` | ExploreViewModel.kt | Explore接口响应时间（API调用时间） | 🔴 100% |
| `TTS_GENERATION_TIME` | TtsManager.kt | TTS生成时间（从发起请求到收到音频URL的完整耗时） | 🟡 调试100%，发布30% |
| `IMAGE_GENERATION_TIME` | ChatViewModel.kt | 图片生成耗时（从发起请求到收到图片URL的完整耗时） | 🟡 调试100%，发布30% |
| `voice_playback_time` | FirebaseManager.Events | 语音播放时间（预留） | 🟡 调试100%，发布30% |
| `image_load_time` | FirebaseManager.Events | 图片加载时间（预留） | 🟡 调试100%，发布20% |
| `page_load_time` | FirebaseManager.Events | 页面加载时间（预留） | 🟡 调试100%，发布30% |
| `database_operation_time` | FirebaseManager.Events | 数据库操作时间（预留） | 🟡 调试100%，发布20% |

### 2.2 性能监控使用

| 功能 | 使用位置 | 业务含义 | 采样率 |
|------|---------|---------|--------|
| `logPerformanceMetric` | ChatViewModel.kt | 记录AI响应时间（API调用时间） | 🔴 100% |
| `logPerformanceMetric` | ExploreViewModel.kt | 记录Explore接口响应时间（API调用时间） | 🔴 100% |
| `logPerformanceMetric` | TtsManager.kt | 记录TTS生成时间（从发起请求到收到音频URL的完整耗时） | 🟡 调试100%，发布30% |
| `logPerformanceMetric` | ChatViewModel.kt | 记录图片生成耗时（从发起请求到收到图片URL的完整耗时） | 🟡 调试100%，发布30% |
| HTTP网络监控 | UnifiedOkHttpClient.kt | 自动监控网络请求性能 | 🟡 调试100%，发布30% |
| 自定义追踪 | FirebaseManager.kt | 自定义性能追踪 | 🟡 调试100%，发布20% |

## 3. Firebase 用户属性

### 3.1 用户身份属性

| 属性名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `user_type` | FirebaseManager.setDeviceInfo() | 用户类型 (vip/free) | 🔴 CRITICAL |
| `subscription_level` | FirebaseManager.setDeviceInfo() | 订阅等级 | 🔴 CRITICAL |
| `app_version` | FirebaseManager.setDeviceInfo() | 应用版本 | 🟡 HIGH |
| `device_type` | FirebaseManager.setDeviceInfo() | 设备类型 (android) | 🟡 HIGH |
| `device_model` | FirebaseManager.setDeviceInfo() | 设备型号 | 🟡 HIGH |
| `os_version` | FirebaseManager.setDeviceInfo() | 操作系统版本 | 🟡 HIGH |
| `app_build_type` | FirebaseManager.setDeviceInfo() | 构建类型 | 🟡 HIGH |
| `user_region` | FirebaseManager.setDeviceInfo() | 用户地区 | 🟡 HIGH |
| `language` | FirebaseManager.setDeviceInfo() | 用户语言 | 🟡 HIGH |

### 3.2 设备信息属性

| 属性名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `app_version_code` | FirebaseManager.setDeviceInfo() | 应用版本号 | 🟡 HIGH |
| `os_version_code` | FirebaseManager.setDeviceInfo() | 系统版本号 | 🟡 HIGH |
| `device_brand` | FirebaseManager.setDeviceInfo() | 设备品牌 | 🟢 MEDIUM |
| `device_manufacturer` | FirebaseManager.setDeviceInfo() | 设备制造商 | 🟢 MEDIUM |
| `device_product` | FirebaseManager.setDeviceInfo() | 设备产品名 | 🟢 MEDIUM |
| `screen_width` | FirebaseManager.setDeviceInfo() | 屏幕宽度 | 🟢 MEDIUM |
| `screen_height` | FirebaseManager.setDeviceInfo() | 屏幕高度 | 🟢 MEDIUM |
| `screen_density` | FirebaseManager.setDeviceInfo() | 屏幕密度 | 🟢 MEDIUM |
| `screen_density_dpi` | FirebaseManager.setDeviceInfo() | 屏幕DPI | 🟢 MEDIUM |
| `locale_display` | FirebaseManager.setDeviceInfo() | 地区显示名 | 🟢 MEDIUM |
| `is_emulator` | FirebaseManager.setDeviceInfo() | 是否模拟器 | 🟢 MEDIUM |
| `is_rooted` | FirebaseManager.setDeviceInfo() | 是否Root | 🟢 MEDIUM |
| `is_debug` | FirebaseManager.setDeviceInfo() | 是否Debug版本 | 🟡 HIGH |

## 4. Firebase Crashlytics 自定义键

### 4.1 页面追踪键

| 键名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `current_page` | PageTrackingHelper.kt | 当前页面名称 | 🟡 HIGH |
| `current_page_class` | PageTrackingHelper.kt | 当前页面类名 | 🟡 HIGH |
| `page_start_time` | PageTrackingHelper.kt | 页面开始时间 | 🟡 HIGH |
| `page_visible_time` | PageTrackingHelper.kt | 页面可见时间 | ⚪ LOW |
| `page_lifecycle_start_time` | PageTrackingHelper.kt | 页面生命周期开始时间 | ⚪ LOW |
| `time_on_page` | PageTrackingHelper.kt | 页面停留时间 | 🟢 MEDIUM |
| `visible_time_on_page` | PageTrackingHelper.kt | 页面可见时间 | ⚪ LOW |
| `lifecycle_time_on_page` | PageTrackingHelper.kt | 页面生命周期时间 | ⚪ LOW |

### 4.2 聊天相关键

| 键名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `chat_session_id` | ChatViewModel.kt | 聊天会话ID | 🔴 CRITICAL |
| `agent_id` | ChatViewModel.kt | Agent ID | 🔴 CRITICAL |
| `message_count` | ChatViewModel.kt | 消息数量 | 🟡 HIGH |
| `ai_response_time` | ChatViewModel.kt | AI响应时间 | 🟡 HIGH |
| `last_message_length` | ChatViewModel.kt | 最后消息长度 | 🟡 HIGH |
| `last_message_preview` | ChatViewModel.kt | 最后消息预览 | 🟡 HIGH |
| `last_agent_id` | ChatViewModel.kt | 最后Agent ID | 🟡 HIGH |

### 4.3 用户交互键

| 键名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `last_interaction` | PageTrackingHelper.kt | 最后交互行为 | ⚪ LOW |
| `last_interaction_time` | PageTrackingHelper.kt | 最后交互时间 | ⚪ LOW |

### 4.4 错误追踪键

| 键名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `last_error` | PageTrackingHelper.kt | 最后错误信息 | 🔴 CRITICAL |
| `last_error_type` | PageTrackingHelper.kt | 最后错误类型 | 🔴 CRITICAL |
| `error_page` | PageTrackingHelper.kt | 错误发生页面 | 🔴 CRITICAL |
| `last_401_url` | UnifiedOkHttpClient.kt | 最后401错误URL | 🔴 CRITICAL |
| `failed_request_url` | UnifiedOkHttpClient.kt | 失败请求URL | 🔴 CRITICAL |
| `failed_request_duration` | UnifiedOkHttpClient.kt | 失败请求持续时间 | 🔴 CRITICAL |
| `slow_request_url` | UnifiedOkHttpClient.kt | 慢请求URL | 🟡 HIGH |
| `slow_request_duration` | UnifiedOkHttpClient.kt | 慢请求持续时间 | 🟡 HIGH |

### 4.5 网络请求键

| 键名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `last_network_request` | PageTrackingHelper.kt | 最后网络请求 | 🟡 HIGH |
| `last_network_success` | PageTrackingHelper.kt | 最后网络请求是否成功 | 🟡 HIGH |

## 5. 关键参数说明

### 5.1 业务关键参数
- `agent_id`、`agent_name`：Agent相关信息，用于分析用户偏好
- `user_type`：用户类型（vip/free），用于商业分析
- `message_length`、`ai_response_time`：聊天相关指标
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应）
- `end_to_end_time`：端到端时间（从用户点击发送按钮到收到响应的完整时间，包含UI处理、API调用等全部时间），用于衡量真实的用户体验
- `timestamp`：事件时间戳，用于时序分析
- `page_name`、`page_class`：页面名称和类名，用于页面追踪
- `page_source`：页面来源标识，用于统计用户从哪个入口进入页面（详见页面追踪事件说明）
- `page`、`page_size`：分页信息（Explore接口的分页参数）
- `agents_count`：本次接口返回的agents数量（单次请求的数量）
- `current_ui_agents_count`：当前UI中所有已加载的agents总数（累计数量，用于统计界面总agent数）
- `sort_seed`：排序种子（用于Explore刷新时改变排序）
- `response_time`：接口响应时间（Explore接口的API调用时间，毫秒）
- `product_id`、`product_name`、`plan_type`：订阅商品信息，用于订阅分析
- `subscription_id`、`order_id`、`purchase_time`：订阅订单信息（subscription_start事件），用于订阅转化分析
- `google_play_price`、`google_play_currency_code`、`google_play_price_micros`：Google Play原始价格信息
- `displayed_price`、`currency_code`、`price_micros`：UI显示的价格信息
- `price_changed`、`currency_changed`、`micros_changed`：价格变化标识，用于监控价格更新
- `message_id`：消息ID（图片生成相关事件）
- `image_url`、`image_width`、`image_height`：生成的图片信息（成功时）
- `generation_time_ms`：图片生成耗时（从发起请求到收到图片URL的完整耗时，毫秒）
- `error_code`、`error_message`、`error_type`：错误信息（失败时）

### 5.2 性能监控参数
- `duration_ms`、`response_time`：性能指标，用于优化
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应），用于API性能分析
- `end_to_end_time`：端到端时间（从用户操作开始到收到响应的完整时间），用于真实的用户体验分析，比API响应时间更能反映用户感知的延迟
- `generation_time_ms`：图片生成耗时（从发起请求到收到图片URL的完整耗时，毫秒），用于图片生成性能分析
- `time_spent`：页面停留时长，用于用户体验分析
- `success`、`response_code`：成功率和错误分析

### 5.3 错误追踪参数
- `error`、`error_type`：错误信息，用于问题诊断
- `url`、`method`：网络请求信息，用于性能分析

## 6. 业务价值分析

### 6.1 核心业务指标
- **用户行为分析**：页面停留时长、用户交互模式、Agent偏好、Explore页面访问和接口使用情况
- **聊天体验优化**：AI响应时间（API性能）、端到端时间（用户真实感知延迟）、消息发送成功率、语音播放体验
- **Explore数据统计**：Explore接口请求成功率、当前界面agents总数、接口响应时间、分页加载情况
- **性能分析**：通过对比API响应时间和端到端时间，可以识别UI处理、网络延迟、本地处理等各个环节的性能瓶颈
- **商业决策支持**：用户转化路径、功能使用频率、订阅分析、订阅价格变化监控、Explore内容推荐效果
- **订阅定价分析**：Google Play价格获取情况、UI价格显示情况、价格变化对转化的影响
- **问题快速发现**：错误监控、网络性能、应用稳定性、价格更新异常、性能瓶颈定位、Explore接口异常

### 6.2 数据质量保证
- **业务数据完整性**：关键业务事件100%采样，确保数据完整
- **性能数据平衡**：适度采样控制成本，保持数据代表性
- **调试友好**：调试模式下100%采样，便于问题排查

## 7. 实际配置说明

### 7.1 采样配置实现
- **业务数据点**：所有关键业务事件在 `FirebaseManager.kt` 中配置为100%采样
- **性能事件**：保持现有采样配置，调试模式100%，生产环境适度采样
- **禁用事件**：`page_visible`、`page_hidden`、`page_lifecycle` 已禁用

### 7.2 限频配置
- **业务事件**：消息发送等关键事件限频1秒（生产环境）
- **性能事件**：用户交互限频10秒（生产环境），网络请求限频2-5秒
- **调试模式**：所有限频时间减半，便于开发调试

---

*文档更新时间：2025年1月*
*版本：dev_1.3.x*
*基于实际代码分析，确保事件信息的准确性和实用性*
*配置更新：业务数据点100%采样，性能事件保持现有配置*
