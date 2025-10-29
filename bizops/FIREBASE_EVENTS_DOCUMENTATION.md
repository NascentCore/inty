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
| `LOGIN` | FirebaseManager.Events | 预留 | 用户登录 | 🔴 100% |
| `SIGN_UP` | FirebaseManager.Events | 预留 | 用户注册 | 🔴 100% |
| `SCREEN_VIEW` | FirebaseManager.Events | 预留 | 页面访问 | 🔴 100% |
| `SELECT_CONTENT` | FirebaseManager.Events | 预留 | 内容选择 | 🔴 100% |
| `SHARE` | FirebaseManager.Events | 预留 | 分享功能 | 🔴 100% |
| `SEARCH` | FirebaseManager.Events | 预留 | 搜索功能 | 🔴 100% |
| `PURCHASE` | FirebaseManager.Events | 预留 | 购买事件 | 🔴 100% |

### 1.2 应用生命周期事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `app_start` | IntelliMateApp.kt | 无 | 应用启动 | 🔴 100% |
| `billing_release` | IntelliMateApp.kt | 无 | 计费系统释放 | 🔴 100% |

### 1.3 用户认证事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `auth_failure` | NetServiceMgr.kt | `http_code`, `url`, `user_logged_out` | HTTP 401认证失败 | 🔴 100% |
| `user_login` | FirebaseManager.Events | 预留 | 用户登录 | 🔴 100% |
| `user_logout` | FirebaseManager.Events | 预留 | 用户登出 | 🔴 100% |

### 1.4 聊天相关事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `chat_started` | ChatViewModel.kt | `agent_id`, `agent_name`, `user_type`, `timestamp` | 聊天会话开始 | 🔴 100% |
| `message_sent` | ChatViewModel.kt | `agent_id`, `agent_name`, `message_length`, `user_type`, `timestamp` | 消息发送 | 🔴 100% |
| `message_send_success` | ChatViewModel.kt | `agent_id`, `agent_name`, `response_code`, `user_type`, `ai_response_time` | 消息发送成功 | 🔴 100% |
| `message_send_failure` | ChatViewModel.kt | 预留 | 消息发送失败 | 🔴 100% |
| `free_limit_reached` | ChatViewModel.kt | 预留 | 达到免费限制 | 🔴 100% |
| `ai_response_received` | FirebaseManager.Events | 预留 | AI回复接收 | 🔴 100% |

### 1.5 页面追踪事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `page_leave` | PageTrackingHelper.kt | `page_name`, `page_class`, `time_spent`, `visible_time_spent`, `lifecycle_time_spent`, `timestamp` | 页面离开，记录停留时长 | 🔴 100% |
| `page_visible` | PageTrackingHelper.kt | `page_name`, `page_class`, `timestamp` | 页面变为可见 | ⚪ 禁用 |
| `page_hidden` | PageTrackingHelper.kt | `page_name`, `page_class`, `visible_time_spent`, `timestamp` | 页面变为不可见 | ⚪ 禁用 |
| `page_lifecycle` | PageTrackingHelper.kt | `page_name`, `page_class`, `lifecycle_event`, `lifecycle_time_spent`, `timestamp` | 页面生命周期事件 | ⚪ 禁用 |
| `explore_page_view` | ExploreViewModel.kt | 预留 | 探索页面访问 | 🔴 100% |

### 1.6 用户交互事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `user_interaction` | PageTrackingHelper.kt | `action`, `target`, `current_page`, `timestamp` | 用户交互行为 | 🟡 调试100%，发布10% |
| `agent_switch` | FirebaseManager.Events | 预留 | Agent切换 | 🔴 100% |
| `voice_playback_start` | AudioManager.kt | `message_id`, `agent_id`, `agent_name`, `has_audio_url`, `auto_play`, `is_manual_click`, `timestamp` | 语音播放开始 | 🔴 100% |

### 1.7 网络请求事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `network_request` | PageTrackingHelper.kt | `url`, `method`, `success`, `response_time`, `current_page` | 网络请求（通用） | 🟡 调试100%，发布20% |
| `network_retry` | NetServiceMgr.kt | `attempt`, `method`, `url`, `status_code`, `exception_type` | 网络请求重试 | 🟡 调试100%，发布50% |
| `network_final_failure` | NetServiceMgr.kt | `max_retries`, `method`, `url`, `last_error`, `last_error_type` | 网络请求最终失败 | 🔴 100% |
| `slow_request` | NetServiceMgr.kt | `duration_ms`, `method`, `url`, `successful` | 慢请求（>3秒） | 🟡 调试100%，发布30% |
| `very_slow_request` | NetServiceMgr.kt | `duration_ms`, `method`, `url`, `successful` | 极慢请求（>10秒） | 🔴 100% |
| `request_failure` | NetServiceMgr.kt | `duration_ms`, `method`, `url`, `error_type`, `error_message` | 请求失败 | 🔴 100% |

### 1.8 错误监控事件

| 事件名称 | 使用位置 | 参数 | 业务含义 | 采样率 |
|---------|---------|------|---------|--------|
| `app_error` | PageTrackingHelper.kt, NetServiceMgr.kt | `error`, `error_type`, `current_page`, `page_class`, `timestamp` | 应用错误 | 🔴 100% |

## 2. Firebase Performance 性能监控

### 2.1 性能事件常量

| 事件名称 | 使用位置 | 业务含义 | 采样率 |
|---------|---------|---------|--------|
| `ai_response_time` | ChatViewModel.kt | AI响应时间 | 🟡 调试100%，发布50% |
| `tts_generation_time` | FirebaseManager.Events | TTS生成时间（预留） | 🟡 调试100%，发布30% |
| `voice_playback_time` | FirebaseManager.Events | 语音播放时间（预留） | 🟡 调试100%，发布30% |
| `image_load_time` | FirebaseManager.Events | 图片加载时间（预留） | 🟡 调试100%，发布20% |
| `page_load_time` | FirebaseManager.Events | 页面加载时间（预留） | 🟡 调试100%，发布30% |
| `database_operation_time` | FirebaseManager.Events | 数据库操作时间（预留） | 🟡 调试100%，发布20% |

### 2.2 性能监控使用

| 功能 | 使用位置 | 业务含义 | 采样率 |
|------|---------|---------|--------|
| `logPerformanceMetric` | ChatViewModel.kt | 记录AI响应时间 | 🟡 调试100%，发布50% |
| HTTP网络监控 | NetServiceMgr.kt | 自动监控网络请求性能 | 🟡 调试100%，发布30% |
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
| `last_401_url` | NetServiceMgr.kt | 最后401错误URL | 🔴 CRITICAL |
| `network_failure_url` | NetServiceMgr.kt | 网络失败URL | 🔴 CRITICAL |
| `network_failure_retries` | NetServiceMgr.kt | 网络失败重试次数 | 🔴 CRITICAL |
| `network_failure_method` | NetServiceMgr.kt | 网络失败请求方法 | 🔴 CRITICAL |
| `slow_request_url` | NetServiceMgr.kt | 慢请求URL | 🟡 HIGH |
| `slow_request_duration` | NetServiceMgr.kt | 慢请求持续时间 | 🟡 HIGH |
| `failed_request_url` | NetServiceMgr.kt | 失败请求URL | 🔴 CRITICAL |
| `failed_request_duration` | NetServiceMgr.kt | 失败请求持续时间 | 🔴 CRITICAL |

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
- `timestamp`：事件时间戳，用于时序分析

### 5.2 性能监控参数
- `duration_ms`、`response_time`：性能指标，用于优化
- `time_spent`：页面停留时长，用于用户体验分析
- `success`、`response_code`：成功率和错误分析

### 5.3 错误追踪参数
- `error`、`error_type`：错误信息，用于问题诊断
- `url`、`method`：网络请求信息，用于性能分析

## 6. 业务价值分析

### 6.1 核心业务指标
- **用户行为分析**：页面停留时长、用户交互模式、Agent偏好
- **聊天体验优化**：AI响应时间、消息发送成功率、语音播放体验
- **商业决策支持**：用户转化路径、功能使用频率、订阅分析
- **问题快速发现**：错误监控、网络性能、应用稳定性

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
