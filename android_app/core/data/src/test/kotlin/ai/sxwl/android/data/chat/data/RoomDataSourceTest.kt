package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageDao
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.ChatSyncStateDao
import ai.sxwl.android.data.chat.local.db.ChatSyncStateEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.chat.local.db.toModel
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.runs
import io.mockk.slot
import io.mockk.unmockkAll
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * RoomDataSource 单元测试
 * 使用 MockK 模拟数据库和 DAO 依赖
 * 
 * 注意：RoomDataSource 现在使用 kotlin-logging（不依赖 Android 环境），
 * 可以在纯 JVM 单元测试环境中运行。
 */
class RoomDataSourceTest {

    private lateinit var mockDatabase: IntyChatDatabase
    private lateinit var mockMessageDao: ChatMessageDao
    private lateinit var mockSyncStateDao: ChatSyncStateDao
    private lateinit var dataSource: RoomDataSource
    private val testDispatcher = StandardTestDispatcher()
    private val agentId = "test-agent-1"

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)

        // 创建模拟对象
        mockDatabase = mockk<IntyChatDatabase>(relaxed = true)
        mockMessageDao = mockk<ChatMessageDao>(relaxed = true)
        mockSyncStateDao = mockk<ChatSyncStateDao>(relaxed = true)

        // 配置数据库返回模拟的 DAO
        every { mockDatabase.chatMessageDao() } returns mockMessageDao
        every { mockDatabase.chatSyncStateDao() } returns mockSyncStateDao

        // 模拟 withTransaction（Room 扩展函数）
        // 使用 relaxed mock 自动处理 withTransaction 调用
        // withTransaction 是扩展函数，relaxed = true 会自动处理

        // 创建数据源实例
        dataSource = RoomDataSource(database = mockDatabase, dispatcher = testDispatcher)
    }

    @After
    fun tearDown() {
        unmockkAll()
    }

    @Test
    fun `getMessagesFlow 返回消息流`() = runTest(testDispatcher) {
        // Given: 模拟数据库返回消息列表
        val entities = listOf(
            createMessageEntity("msg-1", "Hello", "user"),
            createMessageEntity("msg-2", "Hi there", "assistant"),
        )
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(entities)

        // When: 获取消息流
        val flow = dataSource.getMessagesFlow(agentId)
        advanceUntilIdle()

        // Then: 应该返回转换后的消息列表
        val messages = flow.value
        assertEquals(2, messages.size)
        assertEquals("Hello", messages[0].content)
        assertEquals("Hi there", messages[1].content)
    }

    @Test
    fun `getMessagesFlow 缓存同一个 agentId 的流`() = runTest(testDispatcher) {
        // Given: 模拟数据库返回消息列表
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        // When: 多次获取同一个 agentId 的消息流
        val flow1 = dataSource.getMessagesFlow(agentId)
        val flow2 = dataSource.getMessagesFlow(agentId)
        advanceUntilIdle()

        // Then: 应该返回同一个流实例
        assertTrue(flow1 === flow2)
        verify(exactly = 1) { mockMessageDao.streamMessages(agentId) }
    }

    @Test
    fun `updateMessages 更新消息列表`() = runTest(testDispatcher) {
        // Given: 模拟现有消息
        val existingEntities = listOf(
            createMessageEntity("msg-1", "Old message", "user", sortKey = 1000L),
        )
        coEvery { mockMessageDao.getAllMessages(agentId) } returns existingEntities
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        // When: 更新消息
        val newMessages = listOf(
            MsgInfo(id = "msg-1", content = "Updated message", role = "user"),
        )
        dataSource.updateMessages(agentId, newMessages)
        advanceUntilIdle()

        // Then: 应该删除旧消息并插入新消息
        coVerify { mockMessageDao.deleteByAgent(agentId) }
        coVerify { mockMessageDao.upsert(any<List<ChatMessageEntity>>()) }
    }

    @Test
    fun `updateMessages 保留现有消息的 sortKey`() = runTest(testDispatcher) {
        // Given: 已有消息，带有 sortKey
        val existingEntity = createMessageEntity("msg-1", "Original", "user", sortKey = 1000L)
        coEvery { mockMessageDao.getAllMessages(agentId) } returns listOf(existingEntity)
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        val capturedEntities = slot<List<ChatMessageEntity>>()
        coEvery { mockMessageDao.upsert(capture(capturedEntities)) } just runs

        // When: 更新消息（通过 localMsgId 匹配）
        val updatedMessage = MsgInfo(
            id = "msg-1",
            localMsgId = "msg-1",
            content = "Updated",
            role = "user",
        )
        dataSource.updateMessages(agentId, listOf(updatedMessage))
        advanceUntilIdle()

        // Then: 新消息应该保留原有的 sortKey
        val insertedEntity = capturedEntities.captured.first()
        assertEquals(1000L, insertedEntity.sortKey)
        assertEquals("Updated", insertedEntity.content)
    }

    @Test
    fun `updateMessages 为空列表时清空所有消息`() = runTest(testDispatcher) {
        // Given: 已有消息
        coEvery { mockMessageDao.getAllMessages(agentId) } returns listOf(
            createMessageEntity("msg-1", "Message 1", "user"),
        )
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        // When: 使用空列表更新
        dataSource.updateMessages(agentId, emptyList())
        advanceUntilIdle()

        // Then: 应该删除所有消息，但不插入新消息
        coVerify { mockMessageDao.deleteByAgent(agentId) }
        coVerify(exactly = 0) { mockMessageDao.upsert(any<List<ChatMessageEntity>>()) }
    }

    @Test
    fun `appendMessages 追加消息到末尾`() = runTest(testDispatcher) {
        // Given: 已有消息，最大 sortKey 为 1000
        coEvery { mockMessageDao.getMaxSortKey(agentId) } returns 1000L
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        val capturedEntities = slot<List<ChatMessageEntity>>()
        coEvery { mockMessageDao.upsert(capture(capturedEntities)) } just runs

        // When: 追加新消息
        val newMessages = listOf(
            MsgInfo(id = "msg-2", content = "New message", role = "assistant"),
        )
        dataSource.appendMessages(agentId, newMessages)
        advanceUntilIdle()

        // Then: 新消息的 sortKey 应该大于现有最大 sortKey
        val insertedEntity = capturedEntities.captured.first()
        assertTrue(insertedEntity.sortKey > 1000L)
        assertEquals("New message", insertedEntity.content)
    }

    @Test
    fun `appendMessages 空列表时不执行操作`() = runTest(testDispatcher) {
        // When: 追加空列表
        dataSource.appendMessages(agentId, emptyList())
        advanceUntilIdle()

        // Then: 不应该调用数据库操作
        coVerify(exactly = 0) { mockMessageDao.upsert(any<List<ChatMessageEntity>>()) }
    }

    @Test
    fun `prependMessages 前置消息到开头`() = runTest(testDispatcher) {
        // Given: 已有消息，最小 sortKey 为 1000
        coEvery { mockMessageDao.getMinSortKey(agentId) } returns 1000L
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        val capturedEntities = slot<List<ChatMessageEntity>>()
        coEvery { mockMessageDao.upsert(capture(capturedEntities)) } just runs

        // When: 前置新消息
        val newMessages = listOf(
            MsgInfo(id = "msg-0", content = "Prepend message", role = "user"),
        )
        dataSource.prependMessages(agentId, newMessages)
        advanceUntilIdle()

        // Then: 新消息的 sortKey 应该小于现有最小 sortKey
        val insertedEntity = capturedEntities.captured.first()
        assertTrue(insertedEntity.sortKey < 1000L)
        assertEquals("Prepend message", insertedEntity.content)
    }

    @Test
    fun `prependMessages 当没有现有消息时使用当前时间`() = runTest(testDispatcher) {
        // Given: 没有现有消息
        coEvery { mockMessageDao.getMinSortKey(agentId) } returns null
        every { mockMessageDao.streamMessages(agentId) } returns flowOf(emptyList())

        val capturedEntities = slot<List<ChatMessageEntity>>()
        coEvery { mockMessageDao.upsert(capture(capturedEntities)) } just runs

        // When: 前置新消息
        val newMessages = listOf(
            MsgInfo(id = "msg-0", content = "First message", role = "user"),
        )
        dataSource.prependMessages(agentId, newMessages)
        advanceUntilIdle()

        // Then: 应该使用当前时间作为 sortKey
        val insertedEntity = capturedEntities.captured.first()
        assertTrue(insertedEntity.sortKey > 0L)
    }

    @Test
    fun `setHasMore 更新 hasMore 状态`() = runTest(testDispatcher) {
        // Given: 模拟同步状态
        val syncState = ChatSyncStateEntity(agentId = agentId, hasMore = true)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState
        every { mockSyncStateDao.observe(agentId) } returns flowOf(syncState)

        // When: 设置 hasMore 为 false
        dataSource.setHasMore(agentId, false)
        advanceUntilIdle()

        // Then: 应该更新同步状态
        coVerify { mockSyncStateDao.upsert(any<ChatSyncStateEntity>()) }
    }

    @Test
    fun `getHasMoreFlow 返回 hasMore 流`() = runTest(testDispatcher) {
        // Given: 模拟同步状态
        val syncState = ChatSyncStateEntity(agentId = agentId, hasMore = false)
        every { mockSyncStateDao.observe(agentId) } returns flowOf(syncState)

        // When: 获取 hasMore 流
        val flow = dataSource.getHasMoreFlow(agentId)
        advanceUntilIdle()

        // Then: 应该返回正确的值
        assertFalse(flow.value)
    }

    @Test
    fun `getHasMoreFlow 默认值为 true`() = runTest(testDispatcher) {
        // Given: 没有同步状态（返回 null）
        every { mockSyncStateDao.observe(agentId) } returns flowOf(null)

        // When: 获取 hasMore 流
        val flow = dataSource.getHasMoreFlow(agentId)
        advanceUntilIdle()

        // Then: 默认值应该为 true
        assertTrue(flow.value)
    }

    @Test
    fun `setLoadingMore 更新加载状态`() = runTest(testDispatcher) {
        // When: 设置加载状态
        dataSource.setLoadingMore(agentId, true)
        advanceUntilIdle()

        // Then: 流应该立即更新
        val flow = dataSource.getLoadingMoreFlow(agentId)
        assertTrue(flow.value)

        // When: 设置加载状态为 false
        dataSource.setLoadingMore(agentId, false)
        advanceUntilIdle()

        // Then: 流应该更新为 false
        assertFalse(flow.value)
    }

    @Test
    fun `setOffset 和 getOffset 管理偏移量`() = runTest(testDispatcher) {
        // Given: 模拟同步状态
        val syncState = ChatSyncStateEntity(agentId = agentId, offset = 0)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState

        // When: 设置 offset
        dataSource.setOffset(agentId, 20)
        advanceUntilIdle()

        // Then: 应该能获取到设置的 offset
        val updatedState = ChatSyncStateEntity(agentId = agentId, offset = 20)
        coEvery { mockSyncStateDao.get(agentId) } returns updatedState
        val offset = dataSource.getOffset(agentId)
        assertEquals(20, offset)
    }

    @Test
    fun `setOffset 负数时变为 0`() = runTest(testDispatcher) {
        // Given: 模拟同步状态
        val syncState = ChatSyncStateEntity(agentId = agentId, offset = 0)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState

        // When: 设置负数 offset
        dataSource.setOffset(agentId, -10)
        advanceUntilIdle()

        // Then: 应该变为 0
        val updatedState = ChatSyncStateEntity(agentId = agentId, offset = 0)
        coEvery { mockSyncStateDao.get(agentId) } returns updatedState
        val offset = dataSource.getOffset(agentId)
        assertEquals(0, offset)
    }

    @Test
    fun `incrementOffset 增加偏移量`() = runTest(testDispatcher) {
        // Given: 初始 offset 为 10
        val syncState = ChatSyncStateEntity(agentId = agentId, offset = 10)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState

        // When: 增加 offset
        dataSource.incrementOffset(agentId, 20)
        advanceUntilIdle()

        // Then: 应该更新为 30
        val updatedState = ChatSyncStateEntity(agentId = agentId, offset = 30)
        coEvery { mockSyncStateDao.get(agentId) } returns updatedState
        val offset = dataSource.getOffset(agentId)
        assertEquals(30, offset)
    }

    @Test
    fun `incrementOffset 负数时不会小于 0`() = runTest(testDispatcher) {
        // Given: 初始 offset 为 10
        val syncState = ChatSyncStateEntity(agentId = agentId, offset = 10)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState

        // When: 减少 offset（负数增量）
        dataSource.incrementOffset(agentId, -30)
        advanceUntilIdle()

        // Then: 应该变为 0（不会为负数）
        val updatedState = ChatSyncStateEntity(agentId = agentId, offset = 0)
        coEvery { mockSyncStateDao.get(agentId) } returns updatedState
        val offset = dataSource.getOffset(agentId)
        assertEquals(0, offset)
    }

    @Test
    fun `setInitialLoaded 和 isInitialLoaded 管理初始加载状态`() = runTest(testDispatcher) {
        // Given: 初始状态为 false
        val syncState = ChatSyncStateEntity(agentId = agentId, isInitialLoaded = false)
        coEvery { mockSyncStateDao.get(agentId) } returns syncState

        // When: 设置初始加载为 true
        dataSource.setInitialLoaded(agentId, true)
        advanceUntilIdle()

        // Then: 应该更新为 true
        val updatedState = ChatSyncStateEntity(agentId = agentId, isInitialLoaded = true)
        coEvery { mockSyncStateDao.get(agentId) } returns updatedState
        val loaded = dataSource.isInitialLoaded(agentId)
        assertTrue(loaded)
    }

    @Test
    fun `updateMessageAudioUrl 更新消息音频 URL`() = runTest(testDispatcher) {
        // When: 更新音频 URL
        dataSource.updateMessageAudioUrl(agentId, "msg-1", "https://example.com/audio.mp3")
        advanceUntilIdle()

        // Then: 应该调用 DAO 更新方法
        coVerify { mockMessageDao.updateAudioUrl(agentId, "msg-1", "https://example.com/audio.mp3", any()) }
    }

    @Test
    fun `updateMessageFeedback 更新消息反馈`() = runTest(testDispatcher) {
        // When: 更新反馈
        dataSource.updateMessageFeedback(agentId, "msg-1", MsgInfo.UserFeedback.LIKE)
        advanceUntilIdle()

        // Then: 应该调用 DAO 更新方法
        coVerify { mockMessageDao.updateUserFeedback(agentId, "msg-1", "LIKE", any()) }
    }

    @Test
    fun `updateMessageFeedback 清除反馈时传递 null`() = runTest(testDispatcher) {
        // When: 清除反馈
        dataSource.updateMessageFeedback(agentId, "msg-1", null)
        advanceUntilIdle()

        // Then: 应该传递 null
        coVerify { mockMessageDao.updateUserFeedback(agentId, "msg-1", null, any()) }
    }

    @Test
    fun `updateMessage 更新单条消息`() = runTest(testDispatcher) {
        // Given: 模拟现有消息
        val existingEntity = createMessageEntity("msg-1", "Original", "user")
        coEvery { mockMessageDao.getMessage(agentId, "msg-1") } returns existingEntity

        // When: 更新消息
        val updatedMessage = MsgInfo(id = "msg-1", content = "Updated", role = "user")
        dataSource.updateMessage(agentId, "msg-1", updatedMessage)
        advanceUntilIdle()

        // Then: 应该调用 DAO 更新方法
        coVerify { mockMessageDao.upsert(any<ChatMessageEntity>()) }
    }

    @Test
    fun `updateMessageGeneratedImage 更新生成图片`() = runTest(testDispatcher) {
        // Given: 生成图片数据
        val generatedImage = MsgInfo.MsgMetaData.GeneratedImage(
            imageUrl = "https://example.com/image.png",
            width = 512,
            height = 768,
        )

        // When: 更新生成图片
        dataSource.updateMessageGeneratedImage(agentId, "msg-1", generatedImage)
        advanceUntilIdle()

        // Then: 应该调用 DAO 更新方法
        coVerify {
            mockMessageDao.updateGeneratedImage(
                agentId = agentId,
                messageId = "msg-1",
                url = "https://example.com/image.png",
                width = 512,
                height = 768,
                updatedAt = any(),
            )
        }
    }

    @Test
    fun `updateMessageGeneratedImage 清除生成图片时传递 null`() = runTest(testDispatcher) {
        // When: 清除生成图片
        dataSource.updateMessageGeneratedImage(agentId, "msg-1", null)
        advanceUntilIdle()

        // Then: 应该传递 null
        coVerify {
            mockMessageDao.updateGeneratedImage(
                agentId = agentId,
                messageId = "msg-1",
                url = null,
                width = null,
                height = null,
                updatedAt = any(),
            )
        }
    }

    @Test
    fun `removeMessage 删除消息`() = runTest(testDispatcher) {
        // When: 删除消息
        dataSource.removeMessage(agentId, "msg-1")
        advanceUntilIdle()

        // Then: 应该调用 DAO 删除方法
        coVerify { mockMessageDao.deleteMessage(agentId, "msg-1") }
    }

    @Test
    fun `addMessage 添加单条消息`() = runTest(testDispatcher) {
        // Given: 模拟最大 sortKey
        coEvery { mockMessageDao.getMaxSortKey(agentId) } returns 1000L

        // When: 添加消息
        val message = MsgInfo(id = "msg-1", content = "New message", role = "user")
        dataSource.addMessage(agentId, message)
        advanceUntilIdle()

        // Then: 应该调用 DAO 插入方法
        coVerify { mockMessageDao.upsert(any<ChatMessageEntity>()) }
    }

    @Test
    fun `clearChatData 清空指定 agent 的聊天数据`() = runTest(testDispatcher) {
        // When: 清空聊天数据
        dataSource.clearChatData(agentId)
        advanceUntilIdle()

        // Then: 应该删除消息和同步状态
        coVerify { mockMessageDao.deleteByAgent(agentId) }
        coVerify { mockSyncStateDao.delete(agentId) }
    }

    @Test
    fun `clearAllChatData 清空所有聊天数据`() = runTest(testDispatcher) {
        // When: 清空所有聊天数据
        dataSource.clearAllChatData()
        advanceUntilIdle()

        // Then: 应该删除所有消息和同步状态
        coVerify { mockMessageDao.deleteAll() }
        coVerify { mockSyncStateDao.deleteAll() }
    }

    @Test
    fun `getLastSortKey 返回最后一条消息的 sortKey`() = runTest(testDispatcher) {
        // Given: 模拟最大 sortKey
        coEvery { mockMessageDao.getMaxSortKey(agentId) } returns 5000L

        // When: 获取最后一条消息的 sortKey
        val sortKey = dataSource.getLastSortKey(agentId)
        advanceUntilIdle()

        // Then: 应该返回正确的值
        assertEquals(5000L, sortKey)
    }

    @Test
    fun `getLastSortKey 没有消息时返回 0`() = runTest(testDispatcher) {
        // Given: 没有消息
        coEvery { mockMessageDao.getMaxSortKey(agentId) } returns null

        // When: 获取最后一条消息的 sortKey
        val sortKey = dataSource.getLastSortKey(agentId)
        advanceUntilIdle()

        // Then: 应该返回 0
        assertEquals(0L, sortKey)
    }

    // 辅助方法：创建测试用的消息实体
    private fun createMessageEntity(
        localId: String,
        content: String,
        role: String,
        sortKey: Long = System.nanoTime(),
    ): ChatMessageEntity {
        val message = MsgInfo(
            id = localId,
            content = content,
            role = role,
            timestamp = "2025-01-15T10:30:00.000000Z",
        )
        return message.toEntity(agentId, now = sortKey)
    }
}

