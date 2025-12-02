# 测试覆盖分析

## 现有测试覆盖

### 1. ChatTimestampTest
- ✅ 服务器时间戳保留
- ✅ 本地消息时间戳生成
- ✅ updateMessages 时时间戳保留/更新
- ✅ sortKey 和 timestamp 的独立性
- ✅ prependMessages/appendMessages 时间戳保留
- ✅ addMessage 时间戳生成
- ✅ updateMessage 时间戳保留

### 2. LoadMoreMessagesTest
- ✅ prependMessages 正确插入历史消息（使用更小的 sortKey）

### 3. ChatMessageEntityTest (Unit Test)
- ✅ toEntity 使用 remoteId 作为 stable localId
- ✅ 生成图片移除时清除持久化列

## 缺失的测试场景

### 高优先级（关键功能）

#### 1. updateMessages 保留 sortKey 的逻辑 ✅ **已完成**
**场景**：`updateMessages` 在更新消息时应该保留现有消息的 `sortKey`，避免重新排序
- [x] 测试：更新消息时保留现有 sortKey（通过 localId）
- [x] 测试：更新消息时保留现有 sortKey（通过 remoteId）
- [x] 测试：新消息分配新的 sortKey
- [x] 测试：混合场景（部分消息匹配，部分不匹配）
- [x] 测试：更新后消息顺序保持不变
- [x] 测试：空列表清除所有消息

**实现文件**：`UpdateMessagesTest.kt`

#### 2. 并发场景测试 ✅ **已完成**
**场景**：多个线程同时调用 `appendMessages`/`prependMessages` 时，事务保护应该防止 sortKey 冲突
- [x] 测试：并发 appendMessages 不会产生重复 sortKey
- [x] 测试：并发 prependMessages 不会产生重复 sortKey
- [x] 测试：并发 appendMessages 和 prependMessages 不会产生冲突
- [x] 测试：并发 addMessage 不会产生重复 sortKey
- [x] 测试：并发 updateMessages 保留 sortKey

**实现文件**：`ConcurrencyTest.kt`

#### 3. 同步状态管理 ✅ **已完成**
**场景**：hasMore/offset/isInitialLoaded 的状态管理
- [x] 测试：setHasMore/getHasMoreFlow 正确更新和观察
- [x] 测试：setOffset/getOffset/incrementOffset 正确管理偏移量
- [x] 测试：setInitialLoaded/isInitialLoaded 正确管理初始加载状态
- [x] 测试：offset 不能为负数（max(0, offset)）
- [x] 测试：负数增量处理
- [x] 测试：setLoadingMore/getLoadingMoreFlow
- [x] 测试：不同 agentId 状态隔离
- [x] 测试：Flow 自动更新

**实现文件**：`SyncStateTest.kt`

#### 4. 消息更新操作
**场景**：各种消息更新操作的正确性
- [ ] 测试：updateMessageAudioUrl 正确更新音频 URL
- [ ] 测试：updateMessageFeedback 正确更新反馈（like/dislike/null）
- [ ] 测试：updateMessageGeneratedImage 正确更新生成图片
- [ ] 测试：updateMessageGeneratedImage 设置为 null 时清除图片
- [ ] 测试：updateMessage 正确更新消息内容

#### 5. 消息删除
**场景**：removeMessage 的正确性
- [ ] 测试：removeMessage 正确删除指定消息
- [ ] 测试：删除消息后 StateFlow 正确更新
- [ ] 测试：删除不存在的消息不会崩溃

#### 6. 数据清理
**场景**：clearChatData/clearAllChatData 的正确性
- [ ] 测试：clearChatData 正确清理指定 agent 的数据
- [ ] 测试：clearChatData 清理后 StateFlow 为空
- [ ] 测试：clearChatData 清理后同步状态被删除
- [ ] 测试：clearAllChatData 清理所有 agent 的数据
- [ ] 测试：清理后内存状态（flows）被清除

### 中优先级（边界情况）

#### 7. 空消息列表处理
**场景**：appendMessages/prependMessages 处理空列表
- [ ] 测试：appendMessages 空列表不会崩溃
- [ ] 测试：prependMessages 空列表不会崩溃
- [ ] 测试：空列表不会触发数据库操作

#### 8. prependMessages 边界情况
**场景**：prependMessages 在空数据库时的行为
- [ ] 测试：prependMessages 在空数据库时使用 System.nanoTime()
- [ ] 测试：prependMessages 在有消息时使用 minSortKey - 1

#### 9. addMessage 方法
**场景**：addMessage 的正确性
- [ ] 测试：addMessage 正确添加单条消息
- [ ] 测试：addMessage 分配的 sortKey 单调递增
- [ ] 测试：addMessage 在空数据库时的行为

#### 10. StateFlow 缓存机制
**场景**：StateFlow 的缓存和更新
- [ ] 测试：getMessagesFlow 为同一 agentId 返回相同的 StateFlow 实例
- [ ] 测试：getHasMoreFlow 为同一 agentId 返回相同的 StateFlow 实例
- [ ] 测试：StateFlow 在数据库更新时自动发出新值
- [ ] 测试：多个观察者共享同一个 StateFlow

#### 11. 多 agentId 隔离
**场景**：不同 agentId 的数据隔离
- [ ] 测试：不同 agentId 的消息互不影响
- [ ] 测试：不同 agentId 的同步状态互不影响
- [ ] 测试：clearChatData 只清理指定 agentId 的数据

### 低优先级（辅助功能）

#### 12. getLoadingMoreFlow
**场景**：加载状态的观察
- [ ] 测试：setLoadingMore/getLoadingMoreFlow 正确更新和观察

#### 13. 延迟初始化
**场景**：数据库延迟初始化的正确性
- [ ] 测试：ChatLocalDataSource 在应用未初始化时不会崩溃
- [ ] 测试：延迟初始化后数据库正常工作

## 建议的测试文件结构

```
core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/
├── ChatTimestampTest.kt              # ✅ 已存在 - 时间戳相关测试
├── LoadMoreMessagesTest.kt          # ✅ 已存在 - prependMessages 测试
├── UpdateMessagesTest.kt             # ✅ 已完成 - updateMessages 保留 sortKey 测试
├── ConcurrencyTest.kt                # ✅ 已完成 - 并发场景测试
├── SyncStateTest.kt                  # ✅ 已完成 - 同步状态管理测试
├── MessageUpdateTest.kt              # ❌ 缺失 - 消息更新操作测试
├── MessageDeletionTest.kt            # ❌ 缺失 - 消息删除测试
├── DataCleanupTest.kt                # ❌ 缺失 - 数据清理测试
└── StateFlowTest.kt                  # ❌ 缺失 - StateFlow 机制测试
```

## 测试优先级建议

### Phase 1（立即实现）✅ **已完成**
1. ✅ **UpdateMessagesTest** - updateMessages 保留 sortKey 是关键功能
2. ✅ **ConcurrencyTest** - 并发保护是数据正确性的基础
3. ✅ **SyncStateTest** - 分页状态管理是核心功能

### Phase 2（近期实现）
4. **MessageUpdateTest** - 消息更新是常用功能
5. **DataCleanupTest** - 数据清理是重要功能

### Phase 3（后续实现）
6. **MessageDeletionTest** - 消息删除是辅助功能
7. **StateFlowTest** - StateFlow 机制是基础设施
8. 其他边界情况测试

## 测试工具和模式

### 通用测试模式
```kotlin
@RunWith(AndroidJUnit4::class)
class XxxTest {
    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: ChatLocalDataSource
    private val agentId = "test-agent-xxx"

    @Before
    fun setup() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, IntyChatDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        dataSource = ChatLocalDataSource(database = database)
    }

    @After
    fun tearDown() = runBlocking {
        delay(100) // Wait for Flow emissions
        database.close()
    }

    private suspend fun waitForMessages(agentId: String, expectedSize: Int): List<MsgInfo> {
        return withTimeout(5000) {
            var messages: List<MsgInfo>
            do {
                messages = dataSource.getMessagesFlow(agentId).first()
                if (messages.size < expectedSize) {
                    delay(50)
                }
            } while (messages.size < expectedSize)
            messages
        }
    }
}
```

### 并发测试模式
```kotlin
@Test
fun concurrentAppendMessages() = runBlocking {
    val jobs = (1..10).map { i ->
        async {
            dataSource.appendMessages(agentId, listOf(
                MsgInfo(id = "msg-$i", content = "Message $i", role = "user")
            ))
        }
    }
    jobs.awaitAll()
    
    val messages = waitForMessages(agentId, expectedSize = 10)
    val sortKeys = messages.map { /* extract sortKey */ }.toSet()
    assertEquals(10, sortKeys.size) // 验证没有重复的 sortKey
}
```

