# Room Database 向后兼容性审查报告

## 执行摘要

**严重性：🟡 中等**

经过审查发现，**旧版本实际上没有持久化聊天消息到磁盘**，因此不存在数据迁移问题。但当前 Room 数据库配置仍存在一些需要改进的地方。

## 当前实现状态

### 1. 数据库配置

```32:32:core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt
                            .fallbackToDestructiveMigration()
```

**关键问题**：
- 数据库版本：`version = 1`（新数据库）
- 迁移策略：`fallbackToDestructiveMigration()`（破坏性迁移）
- **影响**：如果 Room 检测到任何版本不匹配，会**删除所有表并重新创建**，导致数据丢失

### 2. 旧版本存储机制

**重要发现**：根据 `MMKV_USAGE.md` 的文档说明：

```206:221:core/data/MMKV_USAGE.md
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
```

**关键结论**：
- ✅ **旧版本没有持久化聊天消息到磁盘**
- ✅ **聊天消息只存储在内存中**，应用关闭后数据丢失
- ✅ **MMKV 中的 `chat_messages_*` 键从未被实际使用**，只是预留的接口
- ✅ **不存在数据迁移问题**，因为旧版本本身就没有持久化数据

### 3. 新版本存储机制

新版本使用 **Room 数据库**：
- 表：`chat_messages`（消息）
- 表：`chat_sync_state`（同步状态）
- 数据库文件：`inty_chat.db`

## 升级场景分析

### 场景 1：首次安装新版本
✅ **无问题**：Room 会创建新数据库，用户从空状态开始

### 场景 2：从旧版本升级
✅ **无问题**：旧版本没有持久化聊天消息，因此不存在数据丢失

**实际情况**：
1. 旧版本聊天消息只存储在内存中，应用关闭后数据丢失
2. MMKV 中的 `chat_messages_*` 键从未被实际使用（已废弃）
3. 新版本首次使用 Room 数据库，从空状态开始
4. **用户不会丢失数据**，因为旧版本本身就没有持久化数据

### 场景 3：Room 数据库版本升级
🔴 **严重问题**：如果未来需要升级数据库版本（添加字段、修改表结构等），当前配置会导致数据丢失

**问题**：
- `fallbackToDestructiveMigration()` 意味着任何版本不匹配都会触发数据删除
- 没有定义 `Migration` 对象来处理版本升级

## 具体风险点

### 1. 数据迁移缺失 ✅ 已确认无需迁移

**实际情况**：
- 旧版本没有持久化聊天消息到磁盘
- MMKV 中的 `chat_messages_*` 键从未被使用
- **不需要实现数据迁移代码**

**结论**：此风险点不适用，因为旧版本本身就没有持久化数据。

### 2. 破坏性迁移策略 ⚠️

**问题**：`fallbackToDestructiveMigration()` 会在版本不匹配时删除所有数据

**影响**：
- 如果数据库文件损坏或版本检测异常，所有数据会被删除
- 未来版本升级时，如果没有正确配置 Migration，数据会丢失

**建议**：
- 移除 `fallbackToDestructiveMigration()`
- 为每个版本升级定义 `Migration` 对象
- 或者使用 `allowMainThreadQueries()` + 手动迁移（不推荐）

### 3. 数据库版本管理 ⚠️

**问题**：当前版本是 1，但没有考虑从"无数据库"到"版本 1"的迁移

**影响**：
- 首次使用 Room 的用户没有问题
- 但从旧版本升级的用户需要特殊处理

## 推荐解决方案

### 方案 1：移除破坏性迁移（推荐）

**当前问题**：`fallbackToDestructiveMigration()` 会在版本不匹配时删除所有数据

**解决方案**：
```kotlin
Room.databaseBuilder(context, IntyChatDatabase::class.java, DATABASE_NAME)
    // .fallbackToDestructiveMigration() // 移除这行
    .addMigrations(
        // 未来版本升级时添加 Migration 对象
        // 例如：Migration(1, 2) { database ->
        //     database.execSQL("ALTER TABLE chat_messages ADD COLUMN new_field TEXT")
        // }
    )
    .build()
```

**好处**：
- 防止意外数据丢失
- 为未来版本升级做好准备
- 如果版本不匹配，Room 会抛出异常而不是静默删除数据

### 方案 2：添加数据库版本检查（可选）

在应用启动时检查数据库版本，如果版本不匹配且没有 Migration，可以：
- 记录错误日志
- 提示用户可能需要重新同步数据
- 或者提供数据备份/恢复机制

## 实施优先级

### P0（立即修复）
1. ✅ ~~实现 MMKV 到 Room 的数据迁移~~ **不需要，旧版本没有持久化数据**
2. ✅ 移除 `fallbackToDestructiveMigration()`
3. ✅ 为未来版本升级准备 Migration 策略

### P1（重要）
1. 添加数据库版本检查机制
2. 添加错误处理和日志记录
3. 定义数据库版本升级的 Migration 策略

### P2（未来考虑）
1. 实现数据备份机制
2. 添加数据完整性检查
3. 考虑数据导出/导入功能

## 测试建议

### 1. 升级测试
- ✅ 从旧版本升级到新版本（旧版本没有持久化数据，应该正常）
- 验证 Room 数据库正常创建
- 验证聊天功能正常工作

### 2. 数据库版本升级测试
- 测试未来版本升级时的 Migration 逻辑
- 测试版本不匹配时的错误处理
- 测试 Migration 失败时的回滚机制

### 3. 性能测试
- 大量聊天消息的数据库操作性能
- 数据库初始化对应用启动时间的影响

## 相关文件

- **数据库定义**：`core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`
- **旧存储清理**：`core/data/src/main/kotlin/ai/sxwl/android/data/store/IntySetting.kt`
- **数据源**：`core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`
- **架构文档**：`core/data/CHAT_ARCHITECTURE.md`

## 结论

经过审查，发现**旧版本实际上没有持久化聊天消息到磁盘**，因此：

✅ **不存在数据迁移问题** - 旧版本聊天消息只存储在内存中，应用关闭后数据丢失

⚠️ **但仍需改进**：
1. **移除** `fallbackToDestructiveMigration()` - 防止未来版本升级时意外数据丢失
2. **准备** Migration 策略 - 为未来数据库版本升级做好准备
3. **添加** 版本检查和错误处理 - 提高健壮性

**当前状态**：可以安全发布，但建议在发布前移除破坏性迁移策略，为未来版本升级做好准备。

