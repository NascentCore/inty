package ai.sxwl.android.data.chat.data

import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.chat.local.db.ChatMessageEntity
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.toEntity
import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * RoomDataSource 单元测试
 * 使用真实的 Room 内存数据库进行测试
 * 
 * 使用 Robolectric 提供 Android 环境，可以创建真实的 Room 数据库实例
 */
@Config(sdk = [33])
@org.junit.runner.RunWith(RobolectricTestRunner::class)
class RoomDataSourceTest {

    private lateinit var database: IntyChatDatabase
    private lateinit var dataSource: RoomDataSource
    private val testDispatcher = StandardTestDispatcher()
    private val agentId = "test-agent-1"

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)

        // 使用真实的 Room 内存数据库
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, IntyChatDatabase::class.java)
            .allowMainThreadQueries()
            .build()

        // 创建数据源实例
        dataSource = RoomDataSource(database = database, dispatcher = testDispatcher)
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun `getMessagesFlow 返回消息流`() = runTest(testDispatcher) {
        // Given: 插入测试消息到数据库
        // 注意：streamMessages 按 sortKey DESC 排序，所以 sortKey 更大的消息会在前面
        val entities = listOf(
            createMessageEntity("msg-1", "Hello", "user", sortKey = 1000L),
            createMessageEntity("msg-2", "Hi there", "assistant", sortKey = 2000L),
        )
        database.chatMessageDao().upsert(entities)
        advanceUntilIdle()

        // When: 获取消息流
        val flow = dataSource.getMessagesFlow(agentId)
        // 等待 Flow 发出初始值
        val messages = flow.first { it.isNotEmpty() }

        // Then: 应该返回转换后的消息列表
        // 按 sortKey DESC 排序，所以 msg-2 (sortKey=2000) 在前，msg-1 (sortKey=1000) 在后
        assertEquals(2, messages.size)
        assertEquals("Hi there", messages[0].content)
        assertEquals("Hello", messages[1].content)
    }

    @Test
    fun `appendMessages 追加消息到末尾`() = runTest(testDispatcher) {
        // Given: 已有消息
        val existingMessage = MsgInfo(id = "msg-1", content = "First", role = "user")
        dataSource.addMessage(agentId, existingMessage)
        advanceUntilIdle()

        // When: 追加新消息
        val newMessage = MsgInfo(id = "msg-2", content = "Second", role = "assistant")
        dataSource.appendMessages(agentId, listOf(newMessage))
        advanceUntilIdle()

        // Then: 新消息应该追加到末尾（sortKey 更大，在降序排序中会在前面）
        val messages = dataSource.getMessagesFlow(agentId).first { it.size == 2 }
        assertEquals(2, messages.size)
        assertEquals("Second", messages[0].content) // 新消息在前（sortKey 更大）
        assertEquals("First", messages[1].content)
    }

    @Test
    fun `prependMessages 前置消息到开头`() = runTest(testDispatcher) {
        // Given: 已有消息
        val existingMessage = MsgInfo(id = "msg-1", content = "Second", role = "user")
        dataSource.addMessage(agentId, existingMessage)
        advanceUntilIdle()

        // When: 前置新消息
        val newMessage = MsgInfo(id = "msg-2", content = "First", role = "assistant")
        dataSource.prependMessages(agentId, listOf(newMessage))
        advanceUntilIdle()

        // Then: 新消息应该前置到开头（sortKey 更小，在降序排序中会在后面）
        val messages = dataSource.getMessagesFlow(agentId).first { it.size == 2 }
        assertEquals(2, messages.size)
        assertEquals("Second", messages[0].content) // 原有消息在前（sortKey 更大）
        assertEquals("First", messages[1].content) // 前置消息在后（sortKey 更小）
    }

    @Test
    fun `updateMessages 更新消息列表`() = runTest(testDispatcher) {
        // Given: 已有消息
        val existingMessage = MsgInfo(id = "msg-1", content = "Original", role = "user")
        dataSource.addMessage(agentId, existingMessage)
        advanceUntilIdle()

        // When: 更新消息
        val updatedMessage = MsgInfo(id = "msg-1", content = "Updated", role = "user")
        dataSource.updateMessages(agentId, listOf(updatedMessage))
        advanceUntilIdle()

        // Then: 消息应该被更新
        val messages = dataSource.getMessagesFlow(agentId).first { it.isNotEmpty() }
        assertEquals(1, messages.size)
        assertEquals("Updated", messages[0].content)
    }

    @Test
    fun `setHasMore 和 getHasMoreFlow 管理同步状态`() = runTest(testDispatcher) {
        // Given: 获取 Flow（这会创建并开始观察）
        val flow = dataSource.getHasMoreFlow(agentId)
        // 等待初始值（默认应该是 true）
        val initialValue = flow.first { true }
        assertTrue(initialValue)
        advanceUntilIdle()

        // When: 设置 hasMore 为 false
        dataSource.setHasMore(agentId, false)
        advanceUntilIdle()

        // Then: Flow 应该返回 false
        val hasMore = flow.first { !it } // 等待值变为 false
        assertFalse(hasMore)

        // When: 设置 hasMore 为 true
        dataSource.setHasMore(agentId, true)
        advanceUntilIdle()

        // Then: Flow 应该返回 true
        val hasMoreTrue = flow.first { it } // 等待值变为 true
        assertTrue(hasMoreTrue)
    }

    @Test
    fun `setOffset 和 getOffset 管理偏移量`() = runTest(testDispatcher) {
        // When: 设置 offset
        dataSource.setOffset(agentId, 20)
        advanceUntilIdle()

        // Then: 应该能获取到设置的 offset
        val offset = dataSource.getOffset(agentId)
        assertEquals(20, offset)

        // When: 设置负数 offset
        dataSource.setOffset(agentId, -10)
        advanceUntilIdle()

        // Then: 应该变为 0（不会为负数）
        val offsetAfterNegative = dataSource.getOffset(agentId)
        assertEquals(0, offsetAfterNegative)
    }

    @Test
    fun `clearChatData 清空指定 agent 的聊天数据`() = runTest(testDispatcher) {
        // Given: 已有消息和同步状态
        val message = MsgInfo(id = "msg-1", content = "Test", role = "user")
        dataSource.addMessage(agentId, message)
        dataSource.setOffset(agentId, 10)
        advanceUntilIdle()

        // When: 清空聊天数据
        dataSource.clearChatData(agentId)
        advanceUntilIdle()

        // Then: 消息应该被清空，offset 应该重置为 0
        val messages = dataSource.getMessagesFlow(agentId).value
        assertEquals(0, messages.size)
        val offset = dataSource.getOffset(agentId)
        assertEquals(0, offset)
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
