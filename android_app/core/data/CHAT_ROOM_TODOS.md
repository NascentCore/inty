# Room Database Improvements TODO

本文档列出了基于以下资源审查后识别的所有改进项：
- Google Inventory App 示例代码
- Medium "7 Pro Tips for Room" 文章
- Daily.dev Room 完整指南

## 🔴 高优先级（优先实施）

### 1. 将事务逻辑移至 DAO，使用 `@Transaction` 注解

**当前状态**：事务逻辑在 `ChatLocalDataSource` 中使用 `withTransaction`

**问题**：违反封装原则，根据最佳实践，事务应该在 DAO 层

**改进方案**：
```kotlin
@Dao
interface ChatMessageDao {
    @Transaction
    suspend fun appendMessages(agentId: String, messages: List<ChatMessageEntity>) {
        val lastSortKey = getMaxSortKey(agentId) ?: 0L
        val baseTime = max(System.nanoTime(), lastSortKey + 1)
        var currentSortKey = baseTime
        upsert(messages.map { it.copy(sortKey = currentSortKey++) })
    }
    
    @Transaction
    suspend fun prependMessages(agentId: String, messages: List<ChatMessageEntity>) {
        val minSortKey = getMinSortKey(agentId) ?: 0L
        val baseTime = if (minSortKey > 0) {
            minSortKey - messages.size - 1
        } else {
            System.nanoTime()
        }
        var currentSortKey = baseTime
        upsert(messages.map { it.copy(sortKey = currentSortKey++) })
    }
    
    @Transaction
    suspend fun updateMessagesWithSortKey(
        agentId: String,
        messages: List<ChatMessageEntity>,
        existingMapByLocalId: Map<String, ChatMessageEntity>,
        existingMapByRemoteId: Map<String, ChatMessageEntity>
    ) {
        deleteByAgent(agentId)
        if (messages.isNotEmpty()) {
            val lastSortKey = existingMapByLocalId.values.maxOfOrNull { it.sortKey } ?: 0L
            val baseTime = max(System.nanoTime(), lastSortKey + 1)
            var currentSortKey = baseTime
            
            upsert(messages.map { msg ->
                val existingEntity = when {
                    msg.localId in existingMapByLocalId -> existingMapByLocalId[msg.localId]
                    msg.remoteId != null && msg.remoteId in existingMapByRemoteId -> 
                        existingMapByRemoteId[msg.remoteId]
                    else -> null
                }
                msg.copy(sortKey = existingEntity?.sortKey ?: currentSortKey++)
            })
        }
    }
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/ChatMessageDao.kt` - 添加 `@Transaction` 方法
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt` - 简化为调用 DAO 方法

**影响**：提高代码封装性，遵循 Room 最佳实践

---

### 2. 显式使用 `context.applicationContext`

**当前状态**：使用 `Utils.getApp()`，可能返回 Activity context

**问题**：可能导致内存泄漏

**改进方案**：
```kotlin
fun getInstance(context: Context = Utils.getApp()): IntyChatDatabase {
    return instance ?: synchronized(this) {
        instance ?: Room.databaseBuilder(
            context.applicationContext,  // 显式使用 applicationContext
            IntyChatDatabase::class.java,
            DATABASE_NAME
        )
            .fallbackToDestructiveMigration()
            .build()
            .also { instance = it }
    }
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`

**影响**：防止内存泄漏

---

### 3. 改进测试中的 Flow 等待模式

**当前状态**：使用 `do-while` 循环轮询

**问题**：效率低，不够优雅

**改进方案**：
```kotlin
// LoadMoreMessagesTest.kt
private suspend fun waitForMessages(agentId: String, expectedSize: Int): List<MsgInfo> {
    return withTimeout(5000) {
        dataSource.getMessagesFlow(agentId)
            .first { it.size >= expectedSize }
    }
}

// SyncStateTest.kt
private suspend fun waitForFlowValue(
    flow: kotlinx.coroutines.flow.StateFlow<Boolean>,
    expectedValue: Boolean,
    timeout: Long = 5000,
): Boolean {
    return withTimeout(timeout) {
        flow.first { it == expectedValue }
    }
}
```

**需要修改的文件**：
- `core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/LoadMoreMessagesTest.kt`
- `core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/SyncStateTest.kt`

**影响**：提高测试代码质量和执行效率

---

## 🟡 中优先级（后续实施）

### 4. 实现正确的数据库迁移策略

**当前状态**：使用 `fallbackToDestructiveMigration()`（仅开发阶段）

**问题**：生产环境会导致数据丢失

**改进方案**：
```kotlin
companion object {
    private val MIGRATION_1_2 = object : Migration(1, 2) {
        override fun migrate(database: SupportSQLiteDatabase) {
            // 当 schema 变更时添加迁移逻辑
            // 例如：database.execSQL("ALTER TABLE chat_messages ADD COLUMN new_field TEXT")
        }
    }
    
    fun getInstance(context: Context = Utils.getApp()): IntyChatDatabase {
        return instance ?: synchronized(this) {
            instance ?: Room.databaseBuilder(
                context.applicationContext,
                IntyChatDatabase::class.java,
                DATABASE_NAME
            )
                .addMigrations(MIGRATION_1_2)
                .build()
                .also { instance = it }
        }
    }
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`

**影响**：生产环境数据安全

---

### 5. 添加数据库预填充回调（如需要）

**当前状态**：没有预填充机制

**改进方案**：
```kotlin
Room.databaseBuilder(context, IntyChatDatabase::class.java, DATABASE_NAME)
    .addCallback(object : RoomDatabase.Callback() {
        override fun onCreate(db: SupportSQLiteDatabase) {
            super.onCreate(db)
            // 如果需要预填充默认数据
            CoroutineScope(Dispatchers.IO).launch {
                // 插入默认数据
            }
        }
    })
    .build()
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`（仅在需要默认数据时）

**影响**：支持默认数据初始化

---

### 6. 优化查询 - 仅选择必要的列

**当前状态**：所有查询使用 `SELECT *`

**改进方案**（如果列表视图不需要所有字段）：
```kotlin
@Query(
    "SELECT localId, remoteId, content, timestamp, sortKey, role " +
    "FROM chat_messages WHERE agentId = :agentId ORDER BY sortKey DESC"
)
fun streamMessageSummaries(agentId: String): Flow<List<MessageSummary>>
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/ChatMessageDao.kt`（可选，仅在性能有问题时）

**影响**：提高查询性能（20-50%）

---

### 7. 添加 DAO 继承以复用通用操作

**当前状态**：没有基础 DAO

**改进方案**：
```kotlin
interface BaseDao<T> {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: T)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entities: List<T>)
}

@Dao
interface ChatMessageDao : BaseDao<ChatMessageEntity> {
    // 特定方法
}

@Dao
interface ChatSyncStateDao : BaseDao<ChatSyncStateEntity> {
    // 特定方法
}
```

**需要修改的文件**：
- 创建 `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/BaseDao.kt`
- 更新 `ChatMessageDao.kt`
- 更新 `ChatSyncStateDao.kt`

**影响**：减少代码重复，提高可维护性

---

### 8. 移除测试中的任意延迟

**当前状态**：使用 `delay(100)`，这是任意的

**改进方案**：
```kotlin
@After
fun tearDown() {
    runBlocking {
        // StateFlow 立即发出，不需要延迟
        // 或者如果需要，使用更确定的方法
    }
    database.close()
}
```

**需要修改的文件**：
- `core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/LoadMoreMessagesTest.kt`
- `core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/SyncStateTest.kt`
- `core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/ChatTimestampTest.kt`

**影响**：提高测试可靠性

---

## 🟢 低优先级（按需考虑）

### 9. 添加 TypeConverters（如果存储复杂类型）

**当前状态**：直接存储字符串（目前可以）

**改进方案**（如果将来需要）：
```kotlin
class Converters {
    @TypeConverter
    fun fromTimestamp(value: String?): Long? = 
        value?.let { Instant.parse(it).toEpochMilli() }
    
    @TypeConverter
    fun toTimestamp(value: Long?): String? = 
        value?.let { Instant.ofEpochMilli(it).toString() }
}

@Database(entities = [...], version = 1)
@TypeConverters(Converters::class)
abstract class IntyChatDatabase : RoomDatabase()
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`（仅在需要时）

**影响**：支持复杂类型存储

---

### 10. 考虑使用 Room Paging 处理大型列表

**当前状态**：使用 Flow 和 StateFlow

**改进方案**（如果消息列表变得非常大）：
```kotlin
@Dao
interface ChatMessageDao {
    @Query("SELECT * FROM chat_messages WHERE agentId = :agentId ORDER BY sortKey DESC")
    fun getMessagesPaged(agentId: String): PagingSource<Int, ChatMessageEntity>
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/ChatMessageDao.kt`
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`（仅在需要性能优化时）

**影响**：提高大型列表性能

---

### 11. 添加外键约束（如果存在关系）

**当前状态**：没有外键（实体是独立的）

**改进方案**（如果添加关系）：
```kotlin
@Entity(
    tableName = "chat_messages",
    foreignKeys = [
        ForeignKey(
            entity = ChatSyncStateEntity::class,
            parentColumns = ["agentId"],
            childColumns = ["agentId"],
            onDelete = ForeignKey.CASCADE
        )
    ]
)
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/ChatMessageEntity.kt`（仅在需要关系时）

**影响**：保证引用完整性

---

### 12. 添加 `distinctUntilChanged()` 到 Flow（如需要）

**当前状态**：使用 `StateFlow`，已经处理了这个问题

**注意**：`StateFlow` 已经防止重复发出，所以可能不需要。只有在切换到普通 `Flow` 时才需要添加。

---

### 13. 添加查询结果缓存（如果频繁访问）

**当前状态**：使用 `StateFlow` 和 `SharingStarted.Eagerly`（已缓存）

**注意**：已经通过 `ChatLocalDataSource` 中的 `StateFlow` 缓存实现。

---

### 14. 考虑使用 `@Relation` 进行一对多查询（如适用）

**当前状态**：没有关系需要建模

**改进方案**（如果添加关系）：
```kotlin
data class AgentWithMessages(
    @Embedded val agent: AgentEntity,
    @Relation(
        parentColumn = "agentId",
        entityColumn = "agentId"
    )
    val messages: List<ChatMessageEntity>
)
```

**需要修改的文件**：创建新文件（仅在添加关系时）

**影响**：简化关系查询

---

## 📝 代码质量改进

### 15. 为数据库操作添加错误处理

**当前状态**：没有显式错误处理

**改进方案**：
```kotlin
suspend fun appendMessages(agentId: String, newMessages: List<MsgInfo>) {
    try {
        withContext(dispatcher) {
            // ... 现有代码
        }
    } catch (e: Exception) {
        LogUtils.e("Failed to append messages: ${e.message}", e)
        FirebaseManager.recordException(e)
        throw e
    }
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`

**影响**：更好的错误追踪和调试

---

### 16. 添加输入验证

**当前状态**：存在一些验证（空检查），但可以更全面

**改进方案**：
```kotlin
suspend fun appendMessages(agentId: String, newMessages: List<MsgInfo>) {
    require(agentId.isNotBlank()) { "agentId cannot be blank" }
    require(newMessages.isNotEmpty()) { "newMessages cannot be empty" }
    // ... 其余代码
}
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`

**影响**：更早发现错误

---

### 17. 记录复杂事务逻辑

**当前状态**：存在一些注释，但 `updateMessages` 中的复杂逻辑可以使用更多文档

**改进方案**：为匹配逻辑和 sortKey 保留策略添加更详细的注释

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatLocalDataSource.kt`（第 77-122 行）

**影响**：提高代码可维护性

---

## ⚡ 性能优化

### 18. 考虑批量操作进行多次更新

**当前状态**：每条消息单独更新

**改进方案**（如果更新多条消息）：
```kotlin
@Query("UPDATE chat_messages SET updatedAt = :updatedAt WHERE agentId = :agentId AND localId IN (:messageIds)")
suspend fun batchUpdateTimestamp(agentId: String, messageIds: List<String>, updatedAt: Long)
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/ChatMessageDao.kt`（仅在需要时）

**影响**：提高批量更新性能

---

### 19. 在调试构建中添加数据库查询日志

**当前状态**：使用 `LogUtils`，但可以添加更详细的查询日志

**改进方案**：
```kotlin
Room.databaseBuilder(context, IntyChatDatabase::class.java, DATABASE_NAME)
    .apply {
        if (BuildConfig.DEBUG) {
            setQueryCallback({ sql, bindArgs ->
                LogUtils.d("Room Query: $sql, Args: ${bindArgs.joinToString()}")
            }, Dispatchers.IO)
        }
    }
    .build()
```

**需要修改的文件**：
- `core/data/src/main/kotlin/ai/sxwl/android/data/chat/local/db/IntyChatDatabase.kt`（可选）

**影响**：更好的调试体验

---

## 📊 优先级总结

### 高优先级（首先实施）
1. ✅ 将事务移至 DAO 使用 `@Transaction`
2. ✅ 显式使用 `context.applicationContext`
3. ✅ 改进测试 Flow 等待模式

### 中优先级（接下来实施）
4. ✅ 实现正确的迁移
5. ✅ 添加预填充回调（如需要）
6. ✅ 优化查询（如需要）
7. ✅ 添加 DAO 继承
8. ✅ 移除任意测试延迟

### 低优先级（按需考虑）
9-14. 高级功能（TypeConverters、Paging、外键等）

### 代码质量
15-17. 错误处理、验证、文档

### 性能
18-19. 批量操作、查询日志

---

## 🚀 推荐实施顺序

### 第 1 周：高优先级项目
- [ ] 任务 #1：将事务移至 DAO
- [ ] 任务 #2：使用 applicationContext
- [ ] 任务 #3：改进测试模式

### 第 2 周：中优先级项目
- [ ] 任务 #4：实现迁移
- [ ] 任务 #5：预填充（如需要）
- [ ] 任务 #6：查询优化（如需要）
- [ ] 任务 #7：DAO 继承
- [ ] 任务 #8：移除测试延迟

### 第 3 周+：低优先级项目
- [ ] 按需实施其他改进

---

## ⚠️ 最重要的事项

**最关键**：任务 #1（将事务移至 DAO）对于更好的架构和可维护性最重要。

---

## 📚 参考资源

- [Google Inventory App 示例](https://github.com/google-developer-training/basic-android-kotlin-compose-training-inventory-app)
- [Medium: 7 Pro Tips for Room](https://medium.com/androiddevelopers/7-pro-tips-for-room-fbadea4bfbd1)
- [Daily.dev: Android Room 完整指南](https://daily.dev/blog/android-room-persistence-library-complete-guide)

---

**最后更新**：2025-01-15

