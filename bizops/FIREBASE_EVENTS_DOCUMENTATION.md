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
| `APP_OPEN` | IntelliMateApp.kt | `remote_config_auto_enable_keep_talking`（可选，Remote Config 获取完成后补充上报）, `remote_config_auto_play_opening_voice`（可选，Remote Config 获取完成后补充上报）, `remote_config_home_page_default_tab_index`（可选，Remote Config 获取完成后补充上报） | 应用启动事件（首次上报无参数，Remote Config 获取完成后补充上报一次带参数的事件） | 🔴 100% |
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | `user_id`, `user_type`, `timestamp` | 用户登录（Firebase内置事件） | 🔴 100% |
| `SIGN_UP` | FirebaseManager.Events | 预留 | 用户注册 | 🔴 100% |
| `SCREEN_VIEW` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp`, `page_source` (可选), 其他自定义参数 | 页面访问（Firebase内置事件，通过 `trackPageView()` 自动记录） | 🔴 100% |
| `SELECT_CONTENT` | FirebaseManager.Events | 预留 | 内容选择 | 🔴 100% |
| `SHARE` | FirebaseManager.Events | 预留 | 分享功能 | 🔴 100% |
| `SEARCH` | FirebaseManager.Events | 预留 | 搜索功能 | 🔴 100% |
| `PURCHASE` | FirebaseManager.Events | 预留 | 购买事件 | 🔴 100% |


### 1.3 用户认证事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `auth_failure` | UnifiedOkHttpClient.kt | `error_code`, `url`, `user_logged_out`, `error_message` | HTTP 401认证失败（`error_code` 为 401，`error_message` 中注明白名单接口） | 🔴 100% |
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | `user_id`, `user_type`, `timestamp` | 用户登录（Firebase内置事件） | 🔴 100% |
| `user_logout` | MainViewModel.kt | `user_id`, `user_type`, `timestamp` | 用户登出 | 🔴 100% |

### 1.4 聊天相关事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `chat_started` | ChatViewModel.kt | `agent_id`, `agent_name`, `user_type`, `timestamp` | 聊天会话开始 | 🔴 100% |
| `message_sent` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_length`, `user_type`, `timestamp` | 消息发送（用户点击发送时触发） | 🔴 100% |
| `message_send_success` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_type`（normal/keep_talking）, `response_code`, `user_type`, `ai_response_time`, `end_to_end_time` | 消息发送成功（包含API响应时间和端到端时间，通过 `message_type` 区分普通消息和 Keep Talking） | 🔴 100% |
| `message_send_failure` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_type`（normal/keep_talking）, `error_message`（包含错误类型信息，格式：`failure: ...` 或 `exception: ClassName, ...`）, `user_type`, `ai_response_time`（failure时）, `end_to_end_time` | 消息发送错误（合并 failure 和 exception，错误类型信息在 `error_message` 中，通过 `message_type` 区分普通消息和 Keep Talking） | 🔴 100% |
| `free_limit_reached` | ChatViewModel.kt | `agent_id`, `agent_name`, `user_type`, `timestamp` | 达到免费限制 | 🔴 100% |

### 1.5 图片生成事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `message_to_image_generation_button_clicked` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `user_type`, `timestamp` | 图片生成开始（按钮点击，请求发起时触发） | 🔴 100% |
| `message_to_image_generation_success` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `image_width`, `image_height`, `user_type`, `generation_time_ms`, `timestamp` | 图片生成成功（包含图片信息和生成耗时） | 🔴 100% |
| `message_to_image_generation_failure` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `error_code`, `error_message`（包含异常类型信息，格式：`exception: ClassName, ...`）, `user_type`, `generation_time_ms`, `timestamp` | 图片生成失败（包含错误信息和生成耗时，包括网络错误和异常，异常类型信息在 `error_message` 中，除生成数量上限超标以外的错误） | 🔴 100% |
| `image_generation_limit_reached` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_id`, `error_code`, `error_message`, `user_type`, `generation_time_ms`, `timestamp` | 图片生成限制达到（免费用户需要订阅或VIP用户达到每日限制，这个限制与其他生图操作累加） | 🔴 100% |

### 1.6 页面追踪事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `SCREEN_VIEW` | PageTrackingHelper.kt, ExploreViewModel.kt | `page_name`, `page_class`, `timestamp`, `page_source` (可选), `default_home_tab` (可选，MainPage/HomePage，值为 "chat"/"explore"/"other"), `current_tab` (可选，HomePage，值为 "chat"/"conversation"/"create"/"explore"/"profile"), 其他自定义参数 | 页面访问（Firebase内置事件，通过 `trackPageView()` 自动记录，`page_name` 统一为 xxxPage 格式，如 ChatPage、ExplorePage、subscriptionPage 等） | 🔴 100% |
| `chat_page_view` | ChatPage.kt | `from_page`（可选）, `page_source`, `agent_id`, `agent_name`, `keep_talking_enabled`, `auto_play_voice_enabled`, `auto_play_animation_enabled` | ChatPage 页面曝光（页面真正可见且成为当前页面时触发，用于分析用户访问 ChatPage 的来源和配置） | 🔴 100% |
| `duration` | PageTrackingHelper.kt | `page_name`, `duration`, `timestamp` | 页面停留时长（页面离开时上报） | 🔴 100% |
| `page_visible` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp` | 页面变为可见 | ⚪ 禁用 |
| `page_hidden` | PageTrackingHelper.kt | `page_name`, `page_class`, `visible_time_spent`, `timestamp` | 页面变为不可见 | ⚪ 禁用 |
| `page_lifecycle` | PageTrackingHelper.kt | `page_name`, `page_class`, `lifecycle_event`, `lifecycle_time_spent`, `timestamp` | 页面生命周期事件 | ⚪ 禁用 |

**页面来源参数说明：**
- `page_source`：页面来源标识，用于统计用户从哪个入口进入页面
  - **Heartbeat**（心跳/回忆页）：进入时通过 `PageTrackingHelper.trackPageView("Heartbeat", "MainActivity", ...)` 上报 SCREEN_VIEW，附加参数 `agent_id`、`page_source`。`page_source` 取值：`more_panel`（聊天更多面板入口）、`message_notify`（聊天消息条中的回忆入口）、`unknown`（未传或其它）。代码位置：`Heartbeat.kt` 的 `toHeartbeat()`，入口：`ChatMorePanel.kt`、`ChatItem.kt`。
  - **subscriptionPage**：`home_expired_dialog`（首页过期VIP对话框）、`chat_page`（聊天页面）、`chat_more_panel`（聊天更多面板）、`profile_upgrade`（个人中心升级按钮）、`settings_subscription`（设置页面订阅管理）、`settings_premium_dialog`（设置页面高级模型对话框）
  - **ChatPage**：
    - `chat_activity`：在 ChatActivity 中（独立页面）
    - `main_activity_home_tab`：在 MainActivity 的 HorizontalPager 中（首次进入或从 chat tab 进入）
    - `from_previous_agent`：在 HorizontalPager 中从上一个 agent 滑动而来
    - ChatActivity 场景下的其他来源：`messages_tab`（消息列表Tab）、`explore_tab`（探索Tab）、`profile_tab`（个人中心Tab）、`push_notification`（消息推送通知）等

**ChatPage 曝光事件说明：**
- `chat_page_view` 事件在 ChatPage 真正可见且成为当前页面时触发（`isCurrentPage == true`）
- 事件包含页面来源、Agent 信息、功能开关状态等关键参数，用于分析用户访问 ChatPage 的行为模式
- 通过 `page_source` 参数可以区分用户是从 ChatActivity 进入还是从 MainActivity 的 HorizontalPager 滑动进入
- 在 HorizontalPager 场景中，可以区分是首次进入/从 chat tab 进入（`main_activity_home_tab`）还是从其他 agent 滑动而来（`from_previous_agent`）
- 通过 `keep_talking_enabled` 和 `auto_play_voice_enabled` 参数可以分析不同配置下的用户行为差异
- 事件上报时机：页面真正曝光时（避免重复上报，仅在关键参数变化时上报）
- **重要**：`chat_page_view` 事件在所有场景下都会上报，与 `SCREEN_VIEW` 事件（由 BaseActivity 或 PageTrackingHelper 触发）是独立的，用于专门追踪 ChatPage 的曝光情况

### 1.7 Explore 数据加载事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `explore_agents_fetch_success` | ExploreViewModel.kt | `page`, `page_size`, `response_time`, `agents_count`, `current_ui_agents_count`, `sort_seed`, `user_type`, `timestamp` | Explore接口请求成功（包含本次返回数量和当前UI累计总数） | 🔴 100% |
| `explore_agents_fetch_error` | ExploreViewModel.kt | `page`, `page_size`, `response_time`, `error_message`（包含错误类型和异常类型信息，格式：`failure: ...` 或 `exception: ClassName, ...`）, `current_ui_agents_count`, `sort_seed`, `user_type`, `timestamp` | Explore接口请求错误（合并 failure 和 exception，错误类型和异常类型信息在 `error_message` 中） | 🔴 100% |

### 1.8 用户交互事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `agent_switch` | ChatViewModel.kt | `from_agent_id`, `from_agent_name`, `to_agent_id`, `to_agent_name`, `switch_method`, `user_type`, `timestamp` | Agent切换 | 🔴 100% |
| `chat_page_click` | ChatViewModel.kt, ChatPage.kt, ChatItem.kt, AudioManager.kt | `click_type`（`voice_play`、`keep_talking`、`message_like`、`message_dislike`、`message_sent`、`message_to_image`、`image speed up`、`call`、`sidebar`、`more`）, `agent_id`, `agent_name`, `message_id`（可选）, `message_length`（可选）, `has_generated_image`（可选）, `is_opening`（可选）, `user_type`（可选）, `is_auto_play`（可选）, `timestamp` | 聊天页面点击 | 🔴 100% |
| `chat_sidebar_click` | ChatSettingsDrawer.kt | `click_type`（`edit_name`、`edit_pronouns`、`edit_persona`、`toggle_keep_talking`、`toggle_auto_play_voice`、`toggle_chat_list_full_screen`、`toggle_auto_play_animation`、`toggle_text_streaming`、`toggle_show_scene_action_button`、`open_models_menu`、`select_model`、`open_font_size_slider`、`user_manual`、`feedback`、`report`、`font_size_reset`、`font_size_cancel`、`update_font_size`）, `agent_id`（可选）, `enabled`（可选，开关操作时）, `timestamp` | 聊天侧边栏点击 | 🔴 100% |
| `chat_more_click` | ChatMorePanel.kt | `click_type`（`reply_style`、`report`、`reset`、`change_outfit`、`feedback`、`call`（语音通话，代码常量 CHAT_MORE_CALL））, `agent_id`, `timestamp` | 聊天更多面板点击 | 🔴 100% |
| `conversations_page_click` | MessagesPage.kt | `click_type`（`MessagesSubscriptionBanner` 等）, `timestamp`（可选） | 会话列表页点击 | 🔴 100% |
| `push_notification_click` | MainActivity.kt | 推送通知点击 | 🔴 100% |

### 1.9 订阅与计费事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `subscription_page_view` | VipCenterContent.kt | `page_source`（可选） | 订阅页曝光（进入订阅/会员中心页时触发） | 🔴 100% |
| `subscription_cta_click` | VipCenterContent.kt | `click_type`（按入口区分）, 其他可选参数 | 订阅页 CTA 点击（点击订阅相关按钮时触发） | 🔴 100% |
| `subscription_success` | BillingPurchaseManager.kt | `product_id`, `order_id`, `purchase_token`, `purchase_time`, `user_type`, `price`（可选）, `currency_code`（可选）, `price_micros`（可选）, `timestamp` | 订阅验证成功（服务端验证成功后触发，包含价格参数） | 🔴 100% |
| `subscription_failure` | BillingPurchaseManager.kt | `product_id`, `order_id`, `purchase_token`, `error_code`（可选）, `error_message`, `purchase_time`, `user_type`, `price`（可选）, `currency_code`（可选）, `price_micros`（可选）, `timestamp` | 订阅验证失败（服务端验证失败、网络请求失败或异常时触发，包含价格参数） | 🔴 100% |
| `subscription_price_view` | VipCenterContent.kt | `product_id`, `product_name`, `plan_type`, `price`, `currency_code`, `price_micros`, `timestamp` | 订阅价格查看（在 vipcenter 界面显示订阅产品价格时触发） | 🔴 100% |

### 1.10 Boost 积分/能量事件

以下事件在 BoostManager.kt 中通过字符串直接上报，未在 FirebaseManager.Events 中定义。

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `boost_token_earned` | BoostManager.kt | `source`, `points`, `agent_name` | 获得积分（如手动发放、月度/每日奖励等） | 🔴 100% |
| `boost_month_reward_claimed` | BoostManager.kt | `points` | 月度 VIP 奖励领取 | 🔴 100% |
| `boost_daily_login_reward_claimed` | BoostManager.kt | `points`, `is_vip` | 每日登录奖励领取 | 🔴 100% |
| `boost_daily_reward_claimed` | BoostManager.kt | `points` | 每日奖励领取 | 🔴 100% |
| `boost_invested` | BoostManager.kt | `agent_id`, `agent_name`, `points` | 对角色投入积分 | 🔴 100% |
| `boost_synced_to_backend` | BoostManager.kt | `agent_id`, `agent_name`, `points` | 积分同步到后端成功 | 🔴 100% |
| `boost_sync_failed` | BoostManager.kt | `agent_id`, `agent_name`, `points` 等 | 积分同步失败 | 🔴 100% |
| `boost_sync_exception` | BoostManager.kt | `agent_id`, `agent_name`, `points` 等 | 积分同步异常 | 🔴 100% |

### 1.11 网络请求事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `slow_request` | UnifiedOkHttpClient.kt | `duration_ms` | 慢请求（>3秒） | 🟡 调试100%，发布30% |
| `very_slow_request` | UnifiedOkHttpClient.kt | `duration_ms` | 极慢请求（>10秒） | 🔴 100% |
| `request_failure` | UnifiedOkHttpClient.kt | `duration_ms`, `error_message`（包含异常类型信息，格式：`exception: ClassName, ...`） | 请求失败（网络请求失败时触发，异常类型信息在 `error_message` 中） | 🔴 100% |

### 1.12 错误监控事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `app_error` | PageTrackingHelper.kt, UnifiedOkHttpClient.kt | `error`（包含错误类型信息，格式：`errorType: error`）, `current_page`, `page_class`, `timestamp` | 应用错误（错误类型信息在 `error` 中） | 🔴 100% |


## 2. Firebase Performance 性能监控

### 2.1 性能事件常量

| 事件名称 | 使用位置 | 业务含义 | 采样率 |
|---------|---------|---------|--------|
| `AI_RESPONSE_TIME` | ChatViewModel.kt | AI响应时间（API调用时间） | 🟡 调试100%，发布30% |
| `EXPLORE_RESPONSE_TIME` | ExploreViewModel.kt | Explore接口响应时间（API调用时间） | 🟡 调试100%，发布30% |
| `TTS_GENERATION_TIME` | TtsManager.kt | TTS生成时间（从发起请求到收到音频URL的完整耗时） | 🟡 调试100%，发布30% |
| `IMAGE_GENERATION_TIME` | ChatViewModel.kt | 图片生成耗时（从发起请求到收到图片URL的完整耗时） | 🟡 调试100%，发布30% |
| `voice_playback_time` | FirebaseManager.Events | 语音播放时间（预留） | 🟡 调试100%，发布30% |
| `image_load_time` | FirebaseManager.Events | 图片加载时间（预留） | 🟡 调试100%，发布20% |
| `page_load_time` | FirebaseManager.Events | 页面加载时间（预留） | 🟡 调试100%，发布30% |
| `database_operation_time` | FirebaseManager.Events | 数据库操作时间（预留） | 🟡 调试100%，发布20% |

### 2.2 性能监控使用

| 功能 | 使用位置 | 业务含义 | 采样率 |
|------|---------|---------|--------|
| `logPerformanceMetric` | ChatViewModel.kt | 记录AI响应时间（API调用时间） | 🟡 调试100%，发布30% |
| `logPerformanceMetric` | ExploreViewModel.kt | 记录Explore接口响应时间（API调用时间） | 🟡 调试100%，发布30% |
| `logPerformanceMetric` | TtsManager.kt | 记录TTS生成时间（从发起请求到收到音频URL的完整耗时） | 🟡 调试100%，发布30% |
| `logPerformanceMetric` | ChatViewModel.kt | 记录图片生成耗时（从发起请求到收到图片URL的完整耗时） | 🟡 调试100%，发布30% |
| HTTP网络监控 | UnifiedOkHttpClient.kt | 自动监控网络请求性能 | 🟡 调试100%，发布30% |
| 自定义追踪 | FirebaseManager.kt | 自定义性能追踪 | 🟡 调试100%，发布20% |

## 3. Firebase 用户属性

### 3.1 用户身份属性

| 属性名称 | 设置位置 | 业务含义 | 优先级 |
|---------|---------|---------|--------|
| `user_id` | FirebaseManager.setUserInfo() | 用户ID，用于在Firebase Console中按userId筛选和查看行为数据 | 🔴 CRITICAL |
| `user_type` | FirebaseManager.setUserInfo() | 用户类型 (vip/free) | 🔴 CRITICAL |
| `subscription_level` | FirebaseManager.setUserInfo() | 订阅等级 | 🔴 CRITICAL |
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
- `default_home_tab`：默认首页 tab 名称（MainPage/HomePage 事件，值为 "chat"/"explore"/"other"），用于分析用户默认进入的 tab
- `current_tab`：当前选中的 tab 名称（HomePage 事件，值为 "chat"/"conversation"/"create"/"explore"/"profile"），用于分析用户实际访问的 tab
- `remote_config_auto_enable_keep_talking`、`remote_config_auto_play_opening_voice`、`remote_config_home_page_default_tab_index`：Remote Config 配置参数（APP_OPEN 事件），用于分析 Remote Config 配置对用户行为的影响
- `keep_talking_enabled`、`auto_play_voice_enabled`、`auto_play_animation_enabled`：ChatPage 功能开关状态，用于分析不同配置下的用户行为（chat_page_view 事件）
- `from_page`：上一页/来源页（chat_page_view 等，可选）
- `source`、`points`、`agent_name`、`is_vip`：Boost 积分相关参数（boost_token_earned、boost_*_claimed、boost_invested 等）
- `page`、`page_size`：分页信息（Explore接口的分页参数）
- `agents_count`：本次接口返回的agents数量（单次请求的数量）
- `current_ui_agents_count`：当前UI中所有已加载的agents总数（累计数量，用于统计界面总agent数）
- `sort_seed`：排序种子（用于Explore刷新时改变排序）
- `response_time`：接口响应时间（API调用时间，毫秒），用于Explore接口和网络请求
- `product_id`、`product_name`、`plan_type`：订阅商品信息，用于订阅分析
- `order_id`、`purchase_token`、`purchase_time`：订阅订单信息（subscription_success/subscription_failure事件），用于订阅转化分析和问题排查
- `price`、`currency_code`、`price_micros`：订阅价格信息（subscription_success/subscription_failure/subscription_price_view事件）
- `message_id`：消息ID（图片生成相关事件）
- `image_width`、`image_height`：生成的图片信息（成功时）
- `generation_time_ms`：图片生成耗时（从发起请求到收到图片URL的完整耗时，毫秒）
- `error_code`、`error_message`：错误信息（失败时），统一使用 `error_` 前缀，错误类型和异常类型信息在 `error_message` 中

### 5.2 性能监控参数
- `duration_ms`、`response_time`：性能指标，用于优化
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应），用于API性能分析
- `end_to_end_time`：端到端时间（从用户操作开始到收到响应的完整时间），用于真实的用户体验分析，比API响应时间更能反映用户感知的延迟
- `generation_time_ms`：图片生成耗时（从发起请求到收到图片URL的完整耗时，毫秒），用于图片生成性能分析
- `duration`：页面停留时长（duration事件），用于用户体验分析
- `success`：操作是否成功（布尔值），统一使用 `success` 而非 `successful`
- `response_code`：响应码（数字），用于网络请求和消息发送成功事件

### 5.3 错误追踪参数
- `error`：错误信息（包含错误类型信息，格式：`errorType: error`），用于问题诊断
- `error_code`：错误代码（HTTP错误时使用，如401），与 `response_code` 含义相同但用于不同上下文
- `error_message`：错误消息（包含错误类型和异常类型信息，格式：`failure: ...` 或 `exception: ClassName, ...`）
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

*文档更新时间：2025年2月*
*版本：dev_1.3.x*
*基于实际代码分析，确保事件信息的准确性和实用性*
*配置更新：业务数据点100%采样，性能事件保持现有配置*
