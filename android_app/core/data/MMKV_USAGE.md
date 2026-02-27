# MMKV 在 IntelliMate 中的使用

## 概述

IntelliMate 使用 [MMKV](https://github.com/Tencent/MMKV)（版本 2.2.4）作为轻量级键值存储，用于存储应用设置、用户偏好、会话状态等数据。所有 MMKV 操作通过 `IntySetting` 单例统一封装，提供类型安全的访问接口。

## 初始化

MMKV 在 `IntySetting` 对象的 `init` 块中自动初始化：

```kotlin
init {
    MMKV.initialize(Utils.getApp())
    allUserSetting = MMKV.defaultMMKV(MMKV.SINGLE_PROCESS_MODE, AppUtils.getPackageName())
    
    curUid = getCurUserID()
    curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
}
```

**初始化时机**：应用启动时，首次访问 `IntySetting` 时自动完成。

## 双实例架构

### 1. `allUserSetting` - 应用级存储
- **模式**：`SINGLE_PROCESS_MODE`（单进程模式）
- **用途**：存储应用级通用数据，所有用户共享
- **实例 ID**：使用包名作为标识
- **典型数据**：
  - 当前用户 ID (`cur_uid`)
  - Guest 模式显示标记 (`show_guest`)
  - 应用级通用数据 (`app_data_*`)

### 2. `curUserSetting` - 用户级存储
- **模式**：`MULTI_PROCESS_MODE`（多进程模式）
- **用途**：存储当前用户的数据，支持多用户切换
- **实例 ID**：`"user_$curUid"`，根据用户 ID 动态创建
- **典型数据**：
  - 用户认证信息（token）
  - 用户偏好设置
  - 会话状态
  - 用户资料

### 用户切换机制

当用户切换时（Guest ↔ Google 账户），会动态创建新的用户级实例：

```kotlin
fun changeUser(uid: String) {
    curUid = uid
    curUserSetting = MMKV.mmkvWithID("user_$curUid", MMKV.MULTI_PROCESS_MODE)
    allUserSetting.putString("cur_uid", uid)
}
```

## 数据分类与键命名规范

### 已迁至 DataStore（不再经 MMKV）

以下 8 个用户级设置已迁移到 `IntySettingsDataStore`（DataStore 存储，不迁移旧 MMKV 记录）：

- `chat_font_size_sp`、`chat_model_id`、`chat_list_full_screen`
- `auto_play_animation`、`text_streaming`、`show_scene_action_button`
- `show_keep_talking`、`auto_play_audio`

对外仍通过 `IntySetting` 的同步 getter/setter 访问，实现见 [IntySettingsDataStore.kt](src/main/kotlin/ai/sxwl/android/data/store/IntySettingsDataStore.kt)。

### 1. 用户认证相关

| 键名 | 类型 | 存储位置 | 说明 |
|------|------|----------|------|
| `cur_uid` | String | `allUserSetting` | 当前用户 ID |
| `token` | String | `curUserSetting` | 访问令牌 |

**API 方法**：
- `getCurUserID(): String`
- `setToken(token: String)`
- `getCurToken(): String`
- `isLogin(): Boolean`
- `login(uid: String, token: String)`
- `logout()`
- `isLoggingOut(): Boolean`

### 2. 应用设置相关

以下键仍存于 MMKV（`curUserSetting`）；部分同组键已迁至 DataStore，见上文「已迁至 DataStore」：

| 键名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `show_keep_talking` | Boolean | `false` | 是否显示 Keep Talking 按钮（**值已迁 DataStore**，MMKV 不再读写） |
| `user_set_keep_talking` | Boolean | `false` | 用户是否手动设置过 Keep Talking |
| `auto_play_audio` | Boolean | `true` | 自动播放语音消息（**值已迁 DataStore**） |
| `user_set_auto_play_voice` | Boolean | `false` | 用户是否手动设置过自动播放 |
| `show_scene_action_button` | Boolean | `false` | 显示场景动作输入按钮（**值已迁 DataStore**） |
| `user_set_scene_action_button` | Boolean | `false` | 用户是否手动设置过场景动作按钮 |

**API 方法**：
- `setShowKeepTalking(show: Boolean)` / `isShowKeepTalking(): Boolean`
- `hasUserSetKeepTalking(): Boolean` / `markUserSetKeepTalking()`
- `setAutoPlayAudio(play: Boolean)` / `isAutoPlayAudio(): Boolean`
- `hasUserSetAutoPlayVoice(): Boolean` / `markUserSetAutoPlayVoice()`
- `setShowSceneActionButton(show: Boolean)` / `isShowSceneActionButton(): Boolean`
- `hasUserSetSceneActionButton(): Boolean` / `markUserSetSceneActionButton()`

### 3. 会话状态相关

| 键名模式 | 类型 | 说明 |
|----------|------|------|
| `conversation_pinned_{agentID}` | Boolean | 会话是否置顶 |
| `conversation_hidden_{agentID}` | Boolean | 会话是否隐藏 |
| `conversation_hidden_time_{agentID}` | Long | 会话隐藏时间戳 |

**API 方法**：
- `setConversationPinned(agentId: String, pinned: Boolean)` / `isConversationPinned(agentId: String): Boolean`
- `setConversationHidden(agentId: String, hidden: Boolean)` / `isConversationHidden(agentId: String): Boolean`
- `getConversationHiddenTime(agentId: String): Long`
- `hasNewMessageSinceHidden(agentId: String, lastMessageTime: String): Boolean`

### 4. 用户资料相关

使用 `user_profile_*` 前缀存储用户信息：

| 键名模式 | 类型 | 说明 |
|----------|------|------|
| `user_profile_id` | String | 用户 ID |
| `user_profile_nickname` | String | 昵称 |
| `user_profile_avatar` | String | 头像 URL |
| `user_profile_email` | String | 邮箱 |
| `user_profile_gender` | String | 性别 |
| `user_profile_auth_type` | String | 认证类型 |
| `user_profile_is_active` | Boolean | 是否激活 |
| `user_profile_is_superuser` | Boolean | 是否超级用户 |
| `user_profile_phone` | String | 手机号 |
| `user_profile_age_group` | String/Int | 年龄组 |

**API 方法**：
- `setUserProfileData(key: String, value: String)`
- `getUserProfileData(key: String): String?`
- `setUserProfileBoolean(key: String, value: Boolean)`
- `getUserProfileBoolean(key: String, defaultValue: Boolean): Boolean`
- `setUserProfileInt(key: String, value: Int)`
- `getUserProfileInt(key: String, defaultValue: Int): Int`
- `hasUserProfileData(key: String): Boolean`
- `clearUserProfileData(key: String)`
- `clearAllUserProfileData()`

**使用示例**（通过 `UserProfileManager`）：
```kotlin
// 保存用户资料
UserProfileManager.saveUserProfile(userProfile)

// 读取用户资料
val userProfile = UserProfileManager.getUserProfile()
```

### 5. 应用级数据相关

使用 `app_data_*` 前缀存储应用级通用数据：

| 键名模式 | 类型 | 存储位置 | 说明 |
|----------|------|----------|------|
| `app_data_*` | String | `allUserSetting` | 应用级通用数据（所有用户共享） |

**API 方法**：
- `setAppData(key: String, value: String)`
- `getAppData(key: String): String?`
- `hasAppData(key: String): Boolean`
- `clearAppData(key: String)`
- `getAllAppDataKeys(): Set<String>`

### 6. 订阅相关

| 键名 | 类型 | 说明 |
|------|------|------|
| `resub_reminder_last_time` | Long | 订阅提醒对话框最后显示时间（秒级时间戳） |
| `resub_reminder_show_count` | Int | 订阅提醒对话框显示次数 |

**API 方法**：
- `getLastResubReminderDialogShowTime(): Long`
- `setLastResubReminderDialogShowTime(timestampSeconds: Long)`
- `getResubReminderDialogShowCount(): Int`
- `setResubReminderDialogShowCount(count: Int)`

### 7. 应用更新相关

| 键名 | 类型 | 说明 |
|------|------|------|
| `has_app_update_tips` | Boolean | 是否有可用的应用更新（用于红点标记） |
| `app_google_play_url` | String | Google Play 更新 URL |

**API 方法**：
- `hasAppUpdateTips(): Boolean` / `setAppUpdateTips(showed: Boolean)`
- `appGooglePlayUrl(): String` / `setAppGooglePlayUrl(url: String)`

### 8. 排序种子相关

| 键名 | 类型 | 说明 |
|------|------|------|
| `current_sort_seed` | Int | 推荐接口后端 sort 随机排序的种子 |

**API 方法**：
- `sortSeed(): Int` - 从 MMKV 读取持久化的种子
- `randomSortSeed(): Int` - 每次应用启动时生成新的随机种子（仅内存）
- `updateSortSeed(seed: Int)` - 更新持久化的种子

### 9. Guest 模式相关

| 键名 | 类型 | 存储位置 | 说明 |
|------|------|----------|------|
| `show_guest` | Boolean | `allUserSetting` | 是否显示过 Guest 模式提示 |

**API 方法**：
- `hasShowGuest(): Boolean` / `setShowGuested()`

### 10. 聊天数据相关（已废弃）

以下键名用于存储聊天数据，但当前实现中聊天持久化已禁用，这些方法主要用于清理旧数据：

| 键名模式 | 类型 | 说明 |
|----------|------|------|
| `chat_messages_{agentId}` | String | 聊天消息（JSON 格式，已废弃） |
| `chat_offset_{agentId}` | Int | 分页偏移量（已废弃） |
| `chat_has_more_{agentId}` | Boolean | 是否还有更多消息（已废弃） |
| `chat_initial_loaded_{agentId}` | Boolean | 是否已初始加载（已废弃） |

**API 方法**：
- `clearChatData(agentId: String)` - 清除指定 agent 的聊天数据
- `clearAllChatData()` - 清除所有聊天数据

**注意**：当前聊天数据使用 Room 数据库存储，这些 MMKV 键仅用于清理可能存在的旧数据。

## 使用示例

### 基本使用

```kotlin
// 存储用户偏好
IntySetting.setShowKeepTalking(true)
val shouldShow = IntySetting.isShowKeepTalking()

// 存储会话状态
// 存储用户资料
IntySetting.setUserProfileData("nickname", "John")
val nickname = IntySetting.getUserProfileData("nickname")

// 存储应用级数据
IntySetting.setAppData("feature_flag", "enabled")
val flag = IntySetting.getAppData("feature_flag")
```

### 用户切换

```kotlin
// 登录时
IntySetting.login(uid, token)

// 切换用户
IntySetting.changeUser(newUid)

// 登出
IntySetting.logout()
```

### 批量操作

```kotlin
// 清除所有用户资料
IntySetting.clearAllUserProfileData()

// 获取所有应用级数据键
val keys = IntySetting.getAllAppDataKeys()
```

## 设计特点

### 1. 类型安全
所有访问都通过 `IntySetting` 提供的方法，避免直接使用 MMKV API，减少类型错误。

### 2. 键命名规范
- 使用前缀区分数据类别（`user_profile_*`、`app_data_*`、`conversation_*` 等）
- 使用后缀区分实例（`{agentId}`、`{key}` 等）

### 3. 用户隔离
通过动态创建用户级实例实现多用户数据隔离，支持 Guest ↔ Google 账户切换。

### 4. 默认值处理
所有读取方法都提供合理的默认值，避免空指针异常。

## 注意事项

### 1. 安全风险
- **访问令牌明文存储**：`token` 以明文形式存储在 MMKV 中，存在安全风险（见 `ARCH_CRITIQUES.md` 问题 #10）
- **建议**：考虑使用 Android Keystore 加密敏感数据

### 2. 大列表存储
- **问题**：智能体列表曾以 JSON 格式写入 MMKV，仅有 TTL 无容量上限（见 `ARCH_CRITIQUES.md` 问题 #14）
- **建议**：避免在 MMKV 中存储大型 JSON 列表，使用 Room 数据库存储复杂数据

### 3. 聊天数据迁移
- 当前聊天数据使用 Room 数据库存储
- `clearChatData()` 和 `clearAllChatData()` 方法仅用于清理可能存在的旧 MMKV 数据

### 4. 多进程模式
- `curUserSetting` 使用 `MULTI_PROCESS_MODE`，支持多进程访问
- 注意并发写入可能导致数据竞争，建议通过 `IntySetting` 统一访问

## 相关文件

- **实现文件**：`core/data/src/main/kotlin/ai/sxwl/android/data/store/IntySetting.kt`
- **使用示例**：
  - `app/src/main/kotlin/com/ai/intellimate/utils/UserProfileManager.kt` - 用户资料管理
  - `core/data/src/main/kotlin/ai/sxwl/android/data/billing/BillingStorage.kt` - 计费存储
  - `app/src/main/kotlin/com/ai/intellimate/agent/generate/CreateRoleDraftStorage.kt` - 角色草稿存储
- **架构文档**：`ARCH_CRITIQUES.md` - 架构问题与评估

## 版本信息

- **MMKV 版本**：2.2.4
- **配置位置**：`gradle/libs.versions.toml`
- **依赖声明**：`core/data/build.gradle.kts`

## ProGuard 配置

MMKV 相关类已在 ProGuard 规则中保留：

```proguard
# MMKV 存储
-keep class com.tencent.mmkv.** { *; }
```

配置文件：
- `core/data/proguard-rules.pro`
- `app/proguard-rules.pro`

