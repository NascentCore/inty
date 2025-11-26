# Firebase 自定义维度分析

## 当前状态

**自定义维度总计：39 个**（在 50 个限制范围内，使用率 78%，剩余 11 个配额）✅

**已移除的维度：11 个**（性能/调试相关 5 个 + 低价值业务维度 6 个）
**已简化的参数：2 个**（`default_home_tab_index` + `default_home_tab_name` → `default_home_tab`，`current_tab_index` + `current_tab_name` → `current_tab`）

## 详细统计

### 1. 核心业务维度（必须保留）- 6 个
- `agent_id` ✅
- `agent_name` ✅
- `user_type` ✅
- `message_id` ✅
- `error_message` ✅
- `message_type` ✅

### 2. 订阅相关维度（业务相关，保留）- 13 个
- `product_id` ✅
- `product_name` ✅
- `plan_type` ✅
- `order_id` ✅
- `purchase_token` ✅
- `currency_code` ✅
- `google_play_currency_code` ✅
- `displayed_price` ✅
- `original_price` ✅
- `google_play_price` ✅
- `corrected_price` ✅
- `old_price` ✅
- `old_currency_code` ✅

### 3. 页面追踪维度 - 4 个
- `page_name` ✅（Firebase 内置，必须保留）
- `page_class` ✅（Firebase 内置，必须保留）
- `page_source` ✅（业务相关，分析用户入口）
- `default_home_tab` ✅（业务相关，默认首页 tab 名称）
- `current_tab` ✅（业务相关，当前选中的 tab 名称，HomePage 事件）
- ~~`page_type`~~ ❌（已移除，仅用于 explore 页面，价值较低）

### 4. Agent切换维度（业务相关，保留）- 5 个
- `switch_method` ✅
- `from_agent_id` ✅
- `from_agent_name` ✅
- `to_agent_id` ✅
- `to_agent_name` ✅

### 5. 其他维度 - 1 个
- `user_logged_out` ✅（业务相关，保留）
- ~~`play_status`~~ ❌（已移除，音频播放状态，非核心业务）
- ~~`is_initial_load`~~ ❌（已移除，仅用于 explore 页面，价值较低）
- ~~`success`~~ ❌（已移除，性能相关，非业务）
- ~~`image_url`~~ ❌（已移除，URL 太长，非业务）
- ~~`audio_url`~~ ❌（已移除，URL 太长，非业务）
- ~~`url`~~ ❌（已移除，性能相关，非业务）
- ~~`method`~~ ❌（已移除，性能相关，非业务）
- ~~`message_timestamp`~~ ❌（已移除，已有 timestamp 指标）

### 6. 布尔值维度 - 10 个
- `is_auto_play` ✅（业务相关，保留）
- `has_generated_image` ✅（业务相关，保留）
- `is_opening` ✅（业务相关，保留）
- `is_selected` ✅（订阅相关，保留）
- `is_subscribed` ✅（订阅相关，保留）
- `price_changed` ✅（订阅相关，保留）
- `currency_changed` ✅（订阅相关，保留）
- `micros_changed` ✅（订阅相关，保留）
- `remote_config_auto_enable_keep_talking` ✅（新增，业务相关）
- `remote_config_auto_play_opening_voice` ✅（新增，业务相关）
- ~~`is_manual_click`~~ ❌（已移除，与 is_auto_play 互补，未使用）
- ~~`has_audio_url`~~ ❌（已移除，非核心业务）

## 已移除的维度（共 11 个）

### 性能/调试相关（非业务）- 5 个 ✅
1. `success` - 性能相关，非业务
2. `url` - 性能相关，非业务
3. `method` - 性能相关，非业务
4. `image_url` - URL 太长，非业务
5. `audio_url` - URL 太长，非业务

### 低价值业务维度 - 6 个 ✅
6. `page_type` - 仅用于 explore 页面，价值较低
7. `is_initial_load` - 仅用于 explore 页面，价值较低
8. `play_status` - 音频播放状态，非核心业务（未使用）
9. `is_manual_click` - 与 `is_auto_play` 互补，未使用
10. `has_audio_url` - 非核心业务
11. `message_timestamp` - 已有 `timestamp` 指标，重复

## 当前维度统计

**保留维度：39 个**（在 50 个限制范围内，使用率 78%，剩余 11 个配额）✅

### 保留维度分类
- 核心业务维度：6 个
- 订阅相关维度：13 个
- 页面追踪维度：4 个（简化后，移除 index，只保留 name）
- Agent切换维度：5 个
- 其他维度：1 个（`user_logged_out`）
- 布尔值维度：10 个

**总计：6 + 13 + 4 + 5 + 1 + 10 = 39 个** ✅

## 完成情况

✅ **已完成**：已移除 11 个非业务相关维度，释放配额，为未来扩展留出空间。

