# IntelliMate Firebase 业务事件列表

## 概述

基于实际代码分析，整理IntelliMate应用中所有业务相关的Firebase事件。所有业务事件均配置为100%采样，确保数据完整性。

## 🔴 核心业务事件（100%采样）

### 应用生命周期
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `APP_OPEN` | IntelliMateApp.kt | 应用启动（Firebase内置事件） |
| `BILLING_RELEASE` | IntelliMateApp.kt | 计费系统释放 |

### 用户认证
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `LOGIN` | LoginViewModel.kt, MainActivity.kt | 用户登录（Firebase内置事件） |
| `user_logout` | MainViewModel.kt | 用户登出 |
| `auth_failure` | UnifiedOkHttpClient.kt | HTTP 401认证失败 |

### 聊天核心功能
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `chat_started` | ChatViewModel.kt | 聊天会话开始（第一次发送消息时触发） |
| `agent_switch` | ChatViewModel.kt | Agent切换 |
| `message_sent` | ChatViewModel.kt | 消息发送 |
| `message_send_success` | ChatViewModel.kt | 消息发送成功（包含API响应时间和端到端时间） |
| `message_send_failure` | ChatViewModel.kt | 消息发送失败（包含API响应时间和端到端时间） |
| `message_send_exception` | ChatViewModel.kt | 消息发送异常（包含端到端时间） |
| `free_limit_reached` | ChatViewModel.kt | 达到免费限制 |

### 页面访问
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `page_leave` | PageTrackingHelper.kt | 页面离开（记录停留时长） |
| `explore_page_view` | ExploreViewModel.kt | 探索页面访问 |

### Explore 数据加载
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `explore_agents_fetch_success` | ExploreViewModel.kt | Explore 接口请求成功（包含本次返回数量和当前UI总数） |
| `explore_agents_fetch_failure` | ExploreViewModel.kt | Explore 接口请求失败 |
| `explore_agents_fetch_exception` | ExploreViewModel.kt | Explore 接口请求异常 |

### 订阅与计费
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `subscription_start` | BillingPurchaseManager.kt | 订阅开始（订阅验证成功时触发） |
| `subscription_price_fetched` | BillingPriceManager.kt | 从Google Play获取到的订阅价格 |
| `subscription_price_displayed` | VipCenterContent.kt | UI上显示的订阅价格 |

### 用户交互
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `voice_playback_start` | AudioManager.kt | 语音播放开始 |
| `audio_play_end` | VoicePlayer.kt | 语音播放结束 |
| `pull_up_input` | ChatInput.kt | 拉起输入框 |
| `image_show_success` | AgentBackground.kt | 图片显示成功 |

### 错误监控
| 事件名称 | 使用位置 | 业务含义 |
|---------|---------|---------|
| `app_error` | PageTrackingHelper.kt, UnifiedOkHttpClient.kt | 应用错误 |
| `network_final_failure` | UnifiedOkHttpClient.kt | 网络请求最终失败 |
| `request_failure` | UnifiedOkHttpClient.kt | 请求失败 |
| `very_slow_request` | UnifiedOkHttpClient.kt | 极慢请求（>10秒） |

## 🟡 性能监控事件（适度采样）

### 网络性能
| 事件名称 | 使用位置 | 采样率 |
|---------|---------|--------|
| `network_request` | PageTrackingHelper.kt | 调试100%，发布20% |
| `network_retry` | UnifiedOkHttpClient.kt | 调试100%，发布50%（预留，代码中未使用） |
| `slow_request` | UnifiedOkHttpClient.kt | 调试100%，发布30% |

### 用户行为
| 事件名称 | 使用位置 | 采样率 |
|---------|---------|--------|
| `user_interaction` | PageTrackingHelper.kt | 调试100%，发布100% |

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

### 业务预留事件
- `profile_updated`、`settings_changed`
- `image_generation_start`
- `voice_playback_time`
- `image_load_time`、`page_load_time`、`database_operation_time`
- `network_retry`：配置中已定义，但代码中未使用

## 关键参数

### 业务核心参数
- `agent_id`、`agent_name`：Agent信息
- `user_type`：用户类型（vip/free）
- `message_length`：消息长度
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应）
- `end_to_end_time`：端到端时间（从用户点击发送按钮到收到响应，包含UI处理、API调用等全部时间）
- `timestamp`：事件时间戳

### Explore 参数
- `page`、`page_size`：分页信息（当前页码和每页大小）
- `agents_count`：本次接口返回的agents数量（单次请求的数量）
- `current_ui_agents_count`：当前UI中所有已加载的agents总数（累计数量，用于统计界面总agent数）
- `sort_seed`：排序种子（用于刷新时改变排序）
- `response_time`：接口响应时间（API调用时间，毫秒）

### 订阅价格参数
- `product_id`、`product_name`、`plan_type`：订阅商品信息
- `subscription_id`、`order_id`、`purchase_time`：订阅订单信息（subscription_start事件）
- `google_play_price`、`google_play_currency_code`、`google_play_price_micros`：Google Play原始价格信息
- `displayed_price`、`currency_code`、`price_micros`：UI显示的价格信息
- `corrected_price`、`old_price`：价格变化对比
- `discount_rate`、`original_price`：折扣和原价信息
- `is_selected`、`selected_plan_index`、`total_plans_count`：选择状态和计划数量
- `is_subscribed`：用户订阅状态
- `price_changed`、`currency_changed`、`micros_changed`：价格变化标识

### 性能参数
- `duration_ms`：持续时间
- `response_time`：响应时间（API调用时间）
- `ai_response_time`：AI响应时间（API调用时间，从发起网络请求到收到响应）
- `end_to_end_time`：端到端时间（从用户操作开始到收到响应的完整时间，包含UI处理、API调用等全部时间）
- `time_spent`：页面停留时长
- `success`：操作是否成功

### 错误参数
- `error`、`error_type`：错误信息
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
