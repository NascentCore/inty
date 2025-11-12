# IntelliMate Firebase 业务事件列表

## 概述

基于实际代码分析，整理IntelliMate应用中所有业务相关的Firebase事件。所有业务事件均配置为100%采样，确保数据完整性。

## 🔴 核心业务事件（100%采样）

### 应用生命周期
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `APP_OPEN` | IntelliMateApp.kt | 应用启动（Firebase内置事件） |

### 用户认证
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | 用户登录（Firebase内置事件） |
| `user_logout` | MainViewModel.kt | 用户登出 |
| `auth_failure` | UnifiedOkHttpClient.kt | HTTP 401认证失败（`error_code` 为 401，`error_message` 中注明白名单接口） |

### 聊天核心功能
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `chat_started` | ChatViewModel.kt | 聊天会话开始（第一次发送消息时触发） |
| `agent_switch` | ChatViewModel.kt | Agent切换 |
| `message_sent` | ChatViewModel.kt | 消息发送（用户点击发送时触发，理论上等于 `message_send_success` + `message_send_error` 的总和） |
| `message_send_success` | ChatViewModel.kt | 消息发送成功（包含API响应时间和端到端时间，通过 `message_type` 参数区分普通消息和 Keep Talking） |
| `message_send_error` | ChatViewModel.kt | 消息发送错误（合并 failure 和 exception，错误类型信息在 `error_message` 中，通过 `message_type` 参数区分普通消息和 Keep Talking） |
| `free_limit_reached` | ChatViewModel.kt | 达到免费限制 |

### 图片生成
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `message_to_image_generation_button_clicked` | ChatViewModel.kt | 图片生成开始（请求发起时触发） |
| `message_to_image_generation_success` | ChatViewModel.kt | 图片生成成功（包含图片信息和生成耗时） |
| `message_to_image_generation_failure` | ChatViewModel.kt | 图片生成失败（包含错误信息和生成耗时，包括网络错误和异常） |
| `image_generation_limit_reached` | ChatViewModel.kt | 图片生成限制达到（免费用户需要订阅或VIP用户达到每日限制） |

### 页面访问
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `SCREEN_VIEW` | PageTrackingHelper.kt, ExploreViewModel.kt | 页面访问（Firebase内置事件，通过 `trackPageView()` 自动记录，`page_name` 统一为 xxxPage 格式，如 ChatPage、ExplorePage、subscriptionPage 等，包含 `page_source` 参数） |
| `duration` | PageTrackingHelper.kt | 页面停留时长（页面离开时上报，记录 `page_name` 和 `duration`） |

**页面来源参数说明：**
- `page_source`：页面来源标识，用于统计用户从哪个入口进入页面
  - **subscriptionPage**：`home_expired_dialog`（首页过期VIP对话框）、`chat_page`（聊天页面）、`chat_more_panel`（聊天更多面板）、`profile_upgrade`（个人中心升级按钮）、`settings_subscription`（设置页面订阅管理）、`settings_premium_dialog`（设置页面高级模型对话框）
  - **ChatPage**：`chat_activity`（在 ChatActivity 中）、`main_activity_home_tab`（在 MainActivity 的 HorizontalPager 中）

### Explore 数据加载
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `explore_agents_fetch_success` | ExploreViewModel.kt | Explore 接口请求成功（包含本次返回数量和当前UI总数） |
| `explore_agents_fetch_error` | ExploreViewModel.kt | Explore 接口请求错误（合并 failure 和 exception，错误类型和异常类型信息在 `error_message` 中） |

### 订阅与计费
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `subscription_success` | BillingPurchaseManager.kt | 订阅验证成功（服务端验证成功后触发，包含价格参数：`price`、`currency_code`、`price_micros`） |
| `subscription_failure` | BillingPurchaseManager.kt | 订阅验证失败（服务端验证失败、网络请求失败或异常时触发，包含价格参数：`price`、`currency_code`、`price_micros`） |
| `subscription_price_view` | VipCenterContent.kt | 订阅价格查看（在 vipcenter 界面显示订阅产品价格时触发） |

### 用户交互
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `chat_page_click` | ChatViewModel.kt, AudioManager.kt | 聊天页面点击（通过 `click_type` 区分：`voice_play`、`keep_talking`、`message_like`、`message_dislike`） |
| `chat_sidebar_click` | ChatSettingsDrawer.kt | 聊天侧边栏点击（通过 `click_type` 区分：`edit_name`、`edit_pronouns`、`edit_persona`、`toggle_keep_talking`、`toggle_auto_play_voice`、`report`） |
| `chat_more_click` | ChatMorePanel.kt | 聊天更多面板点击（通过 `click_type` 区分：`reply_style`、`report`） |

### 错误监控
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `app_error` | PageTrackingHelper.kt, UnifiedOkHttpClient.kt | 应用错误 |
| `request_failure` | UnifiedOkHttpClient.kt | 请求失败（网络请求失败时触发） |
| `very_slow_request` | UnifiedOkHttpClient.kt | 极慢请求（>10秒） |

## 🟡 性能监控事件（适度采样）

### 网络性能
| 事件名称 | 使用位置 | 采样率 |
|---------|---------|--------|
| `slow_request` | UnifiedOkHttpClient.kt | 调试100%，发布30% |

## ⚪ 禁用事件

| 事件名称 | 禁用原因 |
|---------|---------|
| `page_visible` | 页面可见性变化过于频繁 |
| `page_hidden` | 页面隐藏事件价值较低 |
| `page_lifecycle` | 生命周期事件过于详细 |

## 预留事件（未实际使用）

### Firebase内置事件
- `SIGN_UP`、`SELECT_CONTENT`、`SHARE`、`SEARCH`、`PURCHASE`
- `SCREEN_VIEW`：通过 `PageTrackingHelper.trackPageView()` 自动记录，无需手动调用

### 业务预留事件（未实际使用）
- `PROFILE_UPDATED`、`SETTINGS_CHANGED`：已从代码中移除（未使用）
- `VOICE_PLAYBACK_TIME`：性能指标，预留
- `IMAGE_LOAD_TIME`、`PAGE_LOAD_TIME`、`DATABASE_OPERATION_TIME`：性能指标，预留

## 关键参数

### 业务核心参数
- `agent_id`、`agent_name`：Agent信息
- `user_type`：用户类型（vip/free）
- `message_length`：消息长度
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应）
- `end_to_end_time`：端到端时间（从用户点击发送按钮到收到响应，包含UI处理、API调用等全部时间）
- `timestamp`：事件时间戳
- `page_name`、`page_class`：页面名称和类名，用于页面追踪
- `page_source`：页面来源标识，用于统计用户从哪个入口进入页面（详见页面访问事件说明）

### Explore 参数
- `page`、`page_size`：分页信息（当前页码和每页大小）
- `agents_count`：本次接口返回的agents数量（单次请求的数量）
- `current_ui_agents_count`：当前UI中所有已加载的agents总数（累计数量，用于统计界面总agent数）
- `sort_seed`：排序种子（用于刷新时改变排序）
- `response_time`：接口响应时间（API调用时间，毫秒）

### 订阅价格参数
- `product_id`、`product_name`、`plan_type`：订阅商品信息
- `order_id`、`purchase_token`、`purchase_time`：订阅订单信息（subscription_success/subscription_failure事件）
- `price`、`currency_code`、`price_micros`：订阅价格信息（subscription_success/subscription_failure/subscription_price_view事件）

### 图片生成参数
- `agent_id`、`agent_name`：Agent信息
- `message_id`：消息ID（要生成图片的消息）
- `image_url`：生成的图片URL（成功时）
- `image_width`、`image_height`：生成的图片尺寸（成功时）
- `generation_time_ms`：图片生成耗时（毫秒，从发起请求到收到响应）
- `error_code`、`error_message`：错误码和错误消息（失败时，异常类型信息在 `error_message` 中，格式：`exception: ClassName, ...`）
- `user_type`：用户类型（vip/free）

### 用户交互参数
- `click_type`：点击类型（chat_page_click/chat_sidebar_click/chat_more_click事件）
  - chat_page_click：`voice_play`、`keep_talking`、`message_like`、`message_dislike`
  - chat_sidebar_click：`edit_name`、`edit_pronouns`、`edit_persona`、`toggle_keep_talking`、`toggle_auto_play_voice`、`report`
  - chat_more_click：`reply_style`、`report`
- `agent_id`、`agent_name`：Agent信息
- `message_id`：消息ID（优先使用服务端id，如果为空则使用本地id作为fallback）
- `message_length`：消息长度
- `has_generated_image`：是否有生成的图片
- `is_opening`：是否为开场消息
- `user_type`：用户类型（vip/free）
- `message_timestamp`：消息时间戳
- `enabled`：开关状态（chat_sidebar_click事件中的开关操作）

### 性能参数
- `duration_ms`：持续时间
- `duration`：页面停留时长（duration事件）
- `response_time`：响应时间（API调用时间）
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应）
- `end_to_end_time`：端到端时间（从用户操作开始到收到响应的完整时间，包含UI处理、API调用等全部时间）
- `success`：操作是否成功

### 错误参数
- `error`：错误信息（包含错误类型信息，格式：`errorType: error`）
- `error_code`：错误代码（HTTP错误时使用，如401）
- `error_message`：错误消息（包含错误类型和异常类型信息，格式：`failure: ...` 或 `exception: ClassName, ...`）
- `url`、`method`：网络请求信息
- `response_code`：响应码

## 业务价值

### 用户行为分析
- **聊天行为**：消息发送频率、Agent偏好、会话时长
- **页面使用**：页面停留时长、访问路径
- **功能使用**：语音播放、图片查看、输入交互
- **Explore使用**：Explore页面访问频率、接口请求成功率、当前界面agents总数统计

### 商业决策支持
- **用户转化**：免费用户转VIP的路径分析
- **功能价值**：各功能的使用频率和用户满意度
- **订阅定价**：订阅价格获取和显示情况监控，分析价格变化对用户转化的影响
- **错误监控**：快速发现和修复问题

### 性能优化
- **AI响应时间**：优化AI服务性能（API调用时间）
- **端到端时间**：优化用户真实感知的延迟（从用户点击到收到响应的完整时间）
- **性能瓶颈识别**：通过对比API响应时间和端到端时间，识别UI处理、网络延迟、本地处理等各个环节的性能瓶颈
- **网络性能**：识别慢请求和失败点
- **用户体验**：页面加载和交互响应优化

---

*文档更新时间：2025年1月*
*版本：dev_1.3.x*
*基于实际代码分析，确保事件信息的准确性*
