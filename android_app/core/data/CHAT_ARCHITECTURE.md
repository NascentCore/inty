# 聊天消息离线优先架构总结

## 架构概述

本次实现了一个基于 **Room 2.8** 的离线优先（Offline-First）聊天消息存储架构，遵循以下核心原则：

1. **单一可信数据源**：Room 数据库作为唯一的数据源
2. **UI 读取本地化**：所有 UI 通过 StateFlow 从本地数据库读取
3. **网络同步后台化**：网络请求只负责刷新数据库，不直接更新 UI
4. **状态持久化**：分页状态（hasMore/offset）持久化到数据库

## 核心组件

### 1. 数据库层（Room）

#### `IntyChatDatabase`
- **实体**：`ChatMessageEntity`（消息）、`ChatSyncStateEntity`（同步状态）
- **版本**：1
- **迁移策略**：`fallbackToDestructiveMigration()`（开发阶段）

#### `ChatMessageEntity`
消息实体包含以下关键字段：
- `localId`：本地唯一标识（PrimaryKey）
- `remoteId`：服务器消息 ID（可为空）
- `sortKey`：**单调递增排序键**（使用 `System.nanoTime()`）
- `timestamp`：**ISO 8601 时间戳**（用于 UI 显示，使用 `System.currentTimeMillis()`）
- `content`、`role`、`audioUrl` 等业务字段

#### `ChatSyncStateEntity`
同步状态实体：
- `agentId`：智能体 ID（PrimaryKey）
- `offset`：分页偏移量
- `hasMore`：是否还有更多消息
- `isInitialLoaded`：是否已初始加载
- `lastSyncedAt`、`updatedAt`：时间戳

### 2. 数据访问层（DAO）

#### `ChatMessageDao`
- `streamMessages(agentId)`：返回 `Flow<List<ChatMessageEntity>>`，按 `sortKey DESC` 排序
- `getMaxSortKey(agentId)` / `getMinSortKey(agentId)`：获取最大/最小 sortKey（用于追加/前置消息）
- `getAllMessages(agentId)`：获取所有消息（用于更新时保留 sortKey）
- CRUD 操作：`upsert`、`deleteMessage`、`deleteByAgent` 等

#### `ChatSyncStateDao`
- `observe(agentId)`：返回同步状态的 Flow
- `upsert`、`delete`：同步状态管理

### 3. 数据源层（DataSource）

#### `ChatLocalDataSource`
**核心职责**：
- 管理 Room 数据库访问
- 提供 StateFlow 给上层
- 处理消息的插入、更新、删除

**关键设计**：

1. **延迟初始化**：
   ```kotlin
   private val db: IntyChatDatabase by lazy {
       database ?: IntyChatDatabase.getInstance()
   }
   ```
   避免在应用未初始化时调用 `Utils.getApp()`

2. **StateFlow 缓存**：
   ```kotlin
   private val messageFlows = ConcurrentHashMap<String, StateFlow<List<MsgInfo>>>()
   ```
   每个 agentId 对应一个 StateFlow，避免重复创建

3. **Flow 转换链**：
   ```kotlin
   messageDao.streamMessages(agentId)
       .map { list -> list.map(ChatMessageEntity::toModel) }
       .stateIn(scope, SharingStarted.Eagerly, emptyList())
   ```
   - Room Flow → 实体列表 → 领域模型列表 → StateFlow

### 4. 仓库层（Repository）

#### `ChatRepositoryImpl`
**职责**：
- 协调本地数据源和远程数据源
- 实现业务逻辑（发送消息、同步、分页加载等）
- 处理网络错误和重试

**关键流程**：

1. **发送消息流程**：
   ```
   用户输入 → 插入本地（userMsg + loadingMsg）→ 发送网络请求 → 
   移除 loading → 插入 AI 回复
   ```

2. **同步流程**：
   ```
   网络获取消息 → 转换为领域模型 → updateMessages → 
   更新数据库 → StateFlow 自动通知 UI
   ```

## 核心机制

### 1. 消息排序机制

#### sortKey 设计
- **用途**：确保消息严格按时间顺序排列
- **生成方式**：使用 `System.nanoTime()`（单调递增，不受系统时钟影响）
- **排序规则**：`ORDER BY sortKey DESC`（新消息在前）

#### 为什么使用 System.nanoTime()？
- **单调性**：保证严格递增，即使系统时钟被调整也不会出现排序错误
- **高精度**：纳秒级精度，避免并发插入时的冲突
- **独立性**：与系统时钟解耦，不受时区、NTP 同步影响

#### 为什么使用 System.currentTimeMillis() 生成 timestamp？
- **实际时间**：timestamp 用于 UI 显示，需要反映真实时间
- **可读性**：可以转换为日期时间字符串展示给用户
- **服务器同步**：服务器返回的时间戳也是基于实际时间

### 2. 消息插入机制

#### `appendMessages`（追加消息）
```kotlin
db.withTransaction {
    val lastSortKey = messageDao.getMaxSortKey(agentId) ?: 0L
    val baseTime = max(System.nanoTime(), lastSortKey + 1)
    var currentSortKey = baseTime
    messageDao.upsert(
        newMessages.map { msg ->
            val sortKey = currentSortKey++
            msg.toEntity(agentId, now = sortKey)
        }
    )
}
```

**特点**：
- **事务保护**：`getMaxSortKey` 和插入在同一事务中，避免竞态条件
- **单调递增**：确保新消息的 sortKey 总是大于现有消息
- **原子性**：多个消息的插入是原子的

#### `prependMessages`（前置消息）
```kotlin
db.withTransaction {
    val minSortKey = messageDao.getMinSortKey(agentId) ?: 0L
    val baseTime = if (minSortKey > 0) {
        minSortKey - newMessages.size - 1
    } else {
        System.nanoTime()
    }
    var currentSortKey = baseTime
    // ... 插入消息
}
```

**特点**：
- 用于在消息列表开头插入历史消息
- sortKey 比现有最小 sortKey 更小

#### `updateMessages`（更新消息）
```kotlin
// 1. 先获取现有消息
val existingMessages = messageDao.getAllMessages(agentId)
val existingMapByLocalId = existingMessages.associateBy { it.localId }
val existingMapByRemoteId = existingMessages.filter { it.remoteId != null }
    .associateBy { it.remoteId!! }

// 2. 在事务中删除并重新插入
db.withTransaction {
    messageDao.deleteByAgent(agentId)
    messageDao.upsert(
        messages.map { msg ->
            // 优先保留现有消息的 sortKey
            val existingEntity = msg.localMsgId.takeIf { it.isNotEmpty() }
                ?.let { existingMapByLocalId[it] }
                ?: msg.id.takeIf { it.isNotEmpty() }
                    ?.let { existingMapByRemoteId[it] }
            val sortKey = existingEntity?.sortKey ?: currentSortKey++
            msg.toEntity(agentId, existing = existingEntity, now = sortKey)
        }
    )
}
```

**关键设计**：
- **保留 sortKey**：更新时优先使用现有消息的 sortKey，避免重新排序
- **匹配策略**：通过 `localId` 和 `remoteId` 匹配现有消息
- **稳定排序**：确保消息在更新后位置不变

### 3. 时间戳处理机制

#### 时间戳生成规则
```kotlin
val resolvedTimestamp = timestamp
    ?: existing?.timestamp
    ?: if (existing == null) {
        // 为本地消息生成 ISO 8601 格式的时间戳
        java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
    } else {
        null
    }
```

**优先级**：
1. **服务器时间戳**：如果消息来自服务器，使用服务器提供的 timestamp
2. **现有时间戳**：如果是更新操作，保留现有的 timestamp
3. **本地生成**：如果是全新的本地消息（如用户输入），从当前时间生成

#### sortKey 与 timestamp 的分离
- **sortKey**：用于数据库排序，使用 `System.nanoTime()`，确保严格单调递增
- **timestamp**：用于 UI 显示，使用 `System.currentTimeMillis()` 或服务器时间，反映实际时间

**为什么分离？**
- sortKey 需要单调性保证排序正确
- timestamp 需要实际时间用于显示
- 两者可以不同步（例如系统时钟被调整时）

### 4. 并发安全机制

#### 事务保护
所有涉及读取和写入的操作都在事务中执行：
```kotlin
db.withTransaction {
    val lastSortKey = messageDao.getMaxSortKey(agentId) ?: 0L
    // ... 基于 lastSortKey 插入消息
}
```

**解决的问题**：
- **竞态条件**：多个线程同时调用 `appendMessages` 时，可能读取到相同的 `lastSortKey`
- **原子性**：确保读取和写入是原子的

#### 延迟初始化
```kotlin
private val db: IntyChatDatabase by lazy {
    database ?: IntyChatDatabase.getInstance()
}
```

**解决的问题**：
- **初始化顺序**：避免在 `Utils.getApp()` 未初始化时调用数据库

### 5. 状态管理机制

#### StateFlow 缓存
```kotlin
private val messageFlows = ConcurrentHashMap<String, StateFlow<List<MsgInfo>>>()

fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> =
    messageFlows.getOrPut(agentId) {
        messageDao.streamMessages(agentId)
            .map { list -> list.map(ChatMessageEntity::toModel) }
            .stateIn(scope, SharingStarted.Eagerly, emptyList())
    }
```

**特点**：
- **单例 Flow**：每个 agentId 只有一个 StateFlow 实例
- **自动更新**：Room Flow 会在数据库变化时自动发出新值
- **共享状态**：多个观察者共享同一个 StateFlow

#### 清理机制
```kotlin
suspend fun clearChatData(agentId: String) =
    withContext(dispatcher) {
        db.withTransaction {
            messageDao.deleteByAgent(agentId)
            syncStateDao.delete(agentId)
        }
        // 等待数据库操作完成后再清理内存状态
        messageFlows.remove(agentId)
        loadingFlows.remove(agentId)
        hasMoreFlows.remove(agentId)
        IntySetting.clearChatData(agentId)
    }
```

**关键点**：
- **suspend 函数**：确保数据库操作完成后再清理内存
- **顺序保证**：先清理数据库，再清理内存状态

## 数据流

### 发送消息流程

```
1. 用户输入消息
   ↓
2. ChatRepositoryImpl.sendMessage()
   ↓
3. 创建 userMsg 和 loadingMsg（无 timestamp）
   ↓
4. ChatLocalDataSource.appendMessages()
   ├─ 在事务中获取 maxSortKey
   ├─ 为每个消息分配递增的 sortKey（System.nanoTime()）
   ├─ toEntity() 为本地消息生成 timestamp（System.currentTimeMillis()）
   └─ 插入数据库
   ↓
5. Room Flow 自动发出新值
   ↓
6. StateFlow 更新
   ↓
7. UI 通过 collectAsState() 获取新消息列表
   ↓
8. 发送网络请求
   ↓
9. 收到 AI 回复后，appendMessages() 插入回复
   ↓
10. UI 自动更新显示 AI 回复
```

### 同步消息流程

```
1. ChatRepositoryImpl.syncLatestMessages()
   ↓
2. 网络请求获取服务器消息
   ↓
3. ChatLocalDataSource.updateMessages()
   ├─ 获取现有消息（保留 sortKey）
   ├─ 匹配现有消息（通过 localId/remoteId）
   ├─ 保留现有 sortKey 或分配新的
   ├─ 使用服务器 timestamp
   └─ 更新数据库
   ↓
4. Room Flow 自动发出新值
   ↓
5. UI 自动更新
```

## 关键修复

### 1. sortKey 使用 System.nanoTime()
**问题**：使用 `System.currentTimeMillis()` 可能导致排序错误（系统时钟调整）
**解决**：改用 `System.nanoTime()` 确保单调递增

### 2. 事务保护 sortKey 生成
**问题**：`getMaxSortKey`/`getMinSortKey` 在事务外调用，存在竞态条件
**解决**：将读取和写入放在同一事务中

### 3. updateMessages 保留 sortKey
**问题**：更新消息时重新分配 sortKey，导致消息位置变化
**解决**：优先使用现有消息的 sortKey

### 4. 延迟数据库初始化
**问题**：`ChatLocalDataSource` 在应用未初始化时创建数据库会崩溃
**解决**：使用 `lazy` 延迟初始化

### 5. clearChatData 改为 suspend
**问题**：数据库操作未完成就清理内存状态，导致竞态条件
**解决**：改为 suspend 函数，确保操作顺序

### 6. 本地消息时间戳生成
**问题**：本地消息（如用户输入）没有 timestamp，UI 无法显示时间
**解决**：在 `toEntity` 中为本地消息生成 ISO 8601 时间戳

### 7. 时间戳与 sortKey 同步
**问题**：在 Repository 层预计算 timestamp，但 sortKey 在 DataSource 层计算，可能不同步
**解决**：移除 Repository 层的时间戳预计算，统一在 DataSource 层处理

## 测试覆盖

### `ChatTimestampTest`（Hermetic Tests）
- **测试类型**：Instrumented tests（需要 Android 环境）
- **数据库**：使用 in-memory Room 数据库
- **测试内容**：
  - 服务器时间戳保留
  - 本地消息时间戳生成
  - 时间戳在更新时的保留
  - sortKey 和 timestamp 的独立性
  - 各种插入/更新场景的时间戳行为

### `ChatMessageEntityTest`（Unit Tests）
- **测试类型**：JUnit tests（纯 Kotlin）
- **测试内容**：
  - `toEntity` 使用 remoteId 作为 stable localId
  - 生成图片移除时清除持久化列

## 构建配置

### META-INF 文件排除
```kotlin
packaging {
    resources {
        excludes += "/META-INF/{AL2.0,LGPL2.1}"
        excludes += "/META-INF/DEPENDENCIES"
        // ... 其他排除项
    }
}
```

**原因**：多个 Apache HTTP Components 依赖包含相同的 META-INF 文件，导致构建冲突

## 性能优化

1. **索引优化**：
   - `agentId` 索引：加速按 agentId 查询
   - `remoteId` 索引：加速消息匹配
   - `(agentId, sortKey)` 复合索引：加速排序查询

2. **Flow 优化**：
   - 使用 `SharingStarted.Eagerly`：立即开始收集
   - StateFlow 缓存：避免重复创建 Flow

3. **事务优化**：
   - 批量操作在同一事务中：减少数据库往返
   - 最小化事务范围：只包含必要的操作

## 架构优势

1. **离线优先**：UI 始终从本地数据库读取，即使网络断开也能显示历史消息
2. **响应迅速**：本地操作立即反映到 UI，无需等待网络
3. **数据一致性**：Room 作为单一可信数据源，避免状态不一致
4. **可测试性**：使用 in-memory 数据库可以轻松编写 hermetic tests
5. **可扩展性**：通过 DAO 和 Repository 模式，易于添加新功能

## 已知限制

1. **迁移策略**：当前使用 `fallbackToDestructiveMigration()`，生产环境需要实现真正的迁移逻辑
2. **数据库大小**：没有实现消息数量限制或自动清理机制
3. **冲突解决**：服务器和本地消息冲突时的解决策略可以进一步优化

## 相关文件

- **数据库定义**：`core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/`
- **数据源**：`core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`
- **仓库**：`core/data/src/main/kotlin/ai/sxwl/android/data/chat/repository/ChatRepositoryImpl.kt`
- **测试**：`core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/ChatTimestampTest.kt`

